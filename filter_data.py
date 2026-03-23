#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import ast
import json
import os
import random
from collections import OrderedDict

from utils import (
    extract_def_for_if,
    rev_extract_all_command,
    handle_node,
    is_integer_in_range,
    find_uncalled_functions,
)

random.seed(42)

additional_patterns_list = [
    "add_collection3d",
    "mlines.line2D",
    "plt.cm.Greens",
    "plt.colorbar",
    "plt.cm.rainbow",
    "plt.cm.viridis",
    "plt.cm.Blues",
    "plt.cm.Reds",
    "plt.cm.ScalarMappable",
    "plt.cm.coolwarm",
]

target_lib_list = ["matplotlib"]


def split_table_by_substring(string_list, substring):
    result = []
    temp = []
    for string in string_list:
        if substring in string:
            if temp:
                result.append(temp)
            temp = []
        else:
            temp.append(string)
    if temp:
        result.append(temp)
    return result


def load_matplotlib_schema(matplotlib_schema_dir, version_list=None):
    if version_list is None:
        version_list = ["3.8.1"]

    matplotlib_schema_dict = OrderedDict()
    for version in version_list:
        matplotlib_schema_path = os.path.join(
            matplotlib_schema_dir, f"matplotlib-{version}.jsonl"
        )
        if not os.path.exists(matplotlib_schema_path):
            raise FileNotFoundError(f"{matplotlib_schema_path} does not exist")

        if version not in matplotlib_schema_dict:
            matplotlib_schema_dict[version] = {}

        with open(matplotlib_schema_path, "r", encoding="utf-8") as fi:
            for line in fi:
                line = line.strip()
                if not line:
                    continue

                line_dict = json.loads(line)

                if line_dict["func_name"] == "__init__":
                    line_dict["func_name"] = line_dict["class_name"]

                if line_dict["func_name"] not in matplotlib_schema_dict[version]:
                    matplotlib_schema_dict[version][line_dict["func_name"]] = []

                if len(line_dict["args"]) > 0:
                    if line_dict["args"][0][0] in ("self", "cls"):
                        line_dict["args"] = line_dict["args"][1:]

                line_dict["args"] = OrderedDict(line_dict["args"])
                line_dict["kargs"] = OrderedDict(line_dict["kargs"])
                matplotlib_schema_dict[version][line_dict["func_name"]].append(line_dict)

    return matplotlib_schema_dict


def getapi2count(line_number2api_name):
    api_list = []
    for line_no in line_number2api_name:
        api_list.append(line_number2api_name[line_no])
    return api_list


def get_inspiration_text(code_line_list, involved_line_no_list):
    inspiration_text = ""
    savefigshow_count = 0
    plt_figure_count = 0
    plt_show_count = 0
    close_count = 0

    for code_line_no in involved_line_no_list:
        curline = code_line_list[code_line_no - 1]
        inspiration_text += curline + "\n"

        if "plt.figure(" in curline:
            plt_figure_count += 1
        if "savefig" in curline:
            savefigshow_count += 1
        if "plt.show(" in curline or "fig.show" in curline:
            plt_show_count += 1
        if "plt.close" in curline or "fig.close" in curline:
            close_count += 1

    counts = [savefigshow_count, plt_figure_count, plt_show_count, close_count]
    max_value = max(counts)
    max_index = counts.index(max_value)
    max_count_api_name = [".savefig", ".figure", ".show", ".close"][max_index]
    return inspiration_text, max_value, max_count_api_name


def extract_inspiration_list_from_code(
    code_text,
    parse_total_lines_threshold,
    matplotlib_func_set,
):
    inspiration_list = []

    try:
        code_normalized = ast.unparse(ast.parse(code_text))
        syntax_error = False
    except Exception:
        syntax_error = True
        code_line_list = code_text.splitlines()
        line_number2api_name = {}

        for idx, line in enumerate(code_line_list):
            cur_code_line = idx + 1
            if (
                "import" in line
                or "def" in line
                or "Class" in line
                or "if" in line
                or "else" in line
            ):
                continue

            best_match_func_name = None
            best_match_len = 0

            for func_name in matplotlib_func_set:
                if f"{func_name}(" in line and (
                    "fig." in line or "ax." in line or "pyplot" in line or "plt." in line
                ):
                    if len(func_name) > best_match_len:
                        best_match_len = len(func_name)
                        best_match_func_name = func_name

            matched = False
            if best_match_len > 0 and best_match_func_name is not None:
                line_number2api_name[cur_code_line] = f"matplotlib.{best_match_func_name}"
                matched = True

            if matched:
                continue

            for pattern in additional_patterns_list:
                if pattern in line:
                    line_number2api_name[cur_code_line] = f"matplotlib.{pattern}"
                    matched = True
                    break

        inspiration_text, _, max_count_api_name = get_inspiration_text(
            code_line_list, sorted(line_number2api_name.keys())
        )

        line_number2api_name = {k: line_number2api_name[k] for k in sorted(line_number2api_name)}
        api2count = getapi2count(line_number2api_name)
        result_splitted = split_table_by_substring(api2count, max_count_api_name)

        for _ in result_splitted:
            inspiration_list.append(inspiration_text)

        return inspiration_list, syntax_error

    code_line_list = code_normalized.splitlines()
    tree = ast.parse(code_normalized)

    def_dict, for_dict, if_dict, class_dict = extract_def_for_if(tree)

    def_class_part_lines = set()
    for def_func_name in def_dict:
        st_line_no, ed_line_no = def_dict[def_func_name][0], def_dict[def_func_name][1]
        for line_no in range(st_line_no, ed_line_no + 1):
            def_class_part_lines.add(line_no)

    for class_name in class_dict:
        st_line_no, ed_line_no = class_dict[class_name][0], class_dict[class_name][1]
        for line_no in range(st_line_no, ed_line_no + 1):
            def_class_part_lines.add(line_no)

    main_part_lines = set(range(1, len(code_line_list) + 1)) - def_class_part_lines
    nodes = rev_extract_all_command(tree)

    library_name2variable_list = {}
    variable2library_name = {}
    other_chosen_line_number_list = []
    line_number2api_name = {}

    variable_list_till_now = []
    for node in nodes:
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            for target_lib in target_lib_list:
                contain_flag, parsed_nodes, variable_list_cur_node = handle_node(
                    node, target_lib=target_lib, variable_list=[]
                )
                if len(variable_list_cur_node) > 0:
                    if target_lib not in library_name2variable_list:
                        library_name2variable_list[target_lib] = variable_list_cur_node
                    else:
                        library_name2variable_list[target_lib] += variable_list_cur_node
                    for var in variable_list_cur_node:
                        variable2library_name[var] = target_lib
                    variable_list_till_now.extend(variable_list_cur_node)
        else:
            contain_flag, parsed_nodes, variable_list_till_now = handle_node(
                node, target_lib="", variable_list=variable_list_till_now
            )
            for item in parsed_nodes:
                if contain_flag and "func_name" in item:
                    line_number2api_name[node.lineno] = f"matplotlib.{item['func_name']}"
            if contain_flag and len(parsed_nodes) > 0:
                other_chosen_line_number_list.append(node.lineno)

    for idx, line in enumerate(code_line_list):
        cur_code_line = idx + 1
        if (
            "import" in line
            or "def" in line
            or "Class" in line
            or "if" in line
            or "else" in line
        ):
            continue

        matched = False
        best_match_func_name = None
        best_match_len = 0

        for func_name in matplotlib_func_set:
            if f"{func_name}(" in line and (
                "fig." in line or "ax." in line or "pyplot." in line or "plt." in line
            ):
                if len(func_name) > best_match_len:
                    best_match_len = len(func_name)
                    best_match_func_name = func_name

        if best_match_len > 0 and best_match_func_name is not None:
            other_chosen_line_number_list.append(cur_code_line)
            line_number2api_name[cur_code_line] = f"matplotlib.{best_match_func_name}"
            matched = True

        if matched:
            continue

        for pattern in additional_patterns_list:
            if pattern in line:
                other_chosen_line_number_list.append(cur_code_line)
                line_number2api_name[cur_code_line] = f"matplotlib.{pattern}"
                matched = True
                break

    line_number2api_name = {key: line_number2api_name[key] for key in sorted(line_number2api_name)}
    cur_api_line_list = sorted(list(line_number2api_name.keys()) + other_chosen_line_number_list)

    extracted_func_def_name2start_line_no = {}
    for def_func_name in def_dict:
        start_line_no = def_dict[def_func_name][0]
        end_line_no = def_dict[def_func_name][1]
        if is_integer_in_range(cur_api_line_list, start_line_no, end_line_no):
            extracted_func_def_name2start_line_no[def_func_name] = start_line_no

    func_name2called_func_name_list = {}
    already_traversaled_func_set = set()
    for func_name in extracted_func_def_name2start_line_no:
        func_name2called_func_name_list[func_name] = []

    for def_func_name in extracted_func_def_name2start_line_no:
        st_line_no, ed_line_no = def_dict[def_func_name]
        for already_traversaled_func in already_traversaled_func_set:
            for line_no in range(st_line_no + 1, ed_line_no + 1):
                code_line = code_line_list[line_no - 1]
                if "." in already_traversaled_func:
                    if f".{already_traversaled_func.split('.')[-1]}(" in code_line:
                        func_name2called_func_name_list[def_func_name].append(
                            {"func_name": already_traversaled_func, "line_no": line_no}
                        )
                elif f"{already_traversaled_func}(" in code_line:
                    func_name2called_func_name_list[def_func_name].append(
                        {"func_name": already_traversaled_func, "line_no": line_no}
                    )
        already_traversaled_func_set.add(def_func_name)

    main_part_called_func_name_list = []
    for line_no in main_part_lines:
        code_line = code_line_list[line_no - 1]
        if (
            "import" in code_line
            or "def" in code_line
            or "Class" in code_line
            or "if" in code_line
            or "else" in code_line
        ):
            continue

        for def_func_name in extracted_func_def_name2start_line_no:
            if "." in def_func_name:
                if f".{def_func_name.split('.')[-1]}(" in code_line:
                    main_part_called_func_name_list.append(
                        {"func_name": def_func_name, "line_no": line_no}
                    )
            elif f"{def_func_name}(" in code_line:
                main_part_called_func_name_list.append(
                    {"func_name": def_func_name, "line_no": line_no}
                )

    func_adj_graph = {
        "##main_part##": [it["func_name"] for it in main_part_called_func_name_list],
    }
    for func_name in func_name2called_func_name_list:
        func_adj_graph[func_name] = [it["func_name"] for it in func_name2called_func_name_list[func_name]]

    result, remaining_functions = find_uncalled_functions(func_adj_graph)
    if len(remaining_functions) > 0:
        result += [remaining_functions]

    for func_list in result:
        fully_involved_line_list = []
        for func_name in func_list:
            if func_name == "##main_part##":
                fully_involved_line_list.extend(list(main_part_lines))
            else:
                st_line_no, ed_line_no = def_dict[func_name]
                fully_involved_line_list.extend(list(range(st_line_no, ed_line_no + 1)))
        fully_involved_line_list = sorted(list(set(fully_involved_line_list)))

        involved_api_line_and_func_line_list = []
        for func_name in func_list:
            if func_name == "##main_part##":
                involved_api_line_and_func_line_list.extend(
                    it["line_no"] for it in main_part_called_func_name_list
                )
                involved_api_line_and_func_line_list.extend(
                    [line_no for line_no in main_part_lines if line_no in cur_api_line_list]
                )
            else:
                involved_api_line_and_func_line_list.extend(
                    [it["line_no"] for it in func_name2called_func_name_list[func_name]]
                )
                st_line_no, ed_line_no = def_dict[func_name]
                involved_api_line_and_func_line_list.extend(
                    [st_line_no]
                    + [
                        line_no
                        for line_no in range(st_line_no, ed_line_no + 1)
                        if line_no in cur_api_line_list
                    ]
                )

        involved_api_line_and_func_line_list = sorted(
            list(set(involved_api_line_and_func_line_list))
        )

        additional_involved_lines = []
        for cur_for_loop_st_line_no in for_dict:
            cur_for_loop_ed_line_no = for_dict[cur_for_loop_st_line_no][1]
            if is_integer_in_range(
                involved_api_line_and_func_line_list,
                cur_for_loop_st_line_no,
                cur_for_loop_ed_line_no,
            ):
                additional_involved_lines.append(cur_for_loop_st_line_no)
                for lineno in line_number2api_name:
                    if cur_for_loop_st_line_no <= lineno <= cur_for_loop_ed_line_no:
                        line_number2api_name[lineno] = f"for.{line_number2api_name[lineno]}"

        involved_api_line_and_func_line_list.extend(additional_involved_lines)
        involved_api_line_and_func_line_list = sorted(
            list(set(involved_api_line_and_func_line_list))
        )

        additional_involved_lines = []
        for cur_if_st_line_no in if_dict:
            cur_if_ed_line_no = if_dict[cur_if_st_line_no][1]
            if is_integer_in_range(
                involved_api_line_and_func_line_list,
                cur_if_st_line_no,
                cur_if_ed_line_no,
            ):
                additional_involved_lines.append(cur_if_st_line_no)
        involved_api_line_and_func_line_list.extend(additional_involved_lines)
        involved_api_line_and_func_line_list = sorted(
            list(set(involved_api_line_and_func_line_list))
        )

        additional_involved_lines = []
        for class_name in class_dict:
            st_line_no, ed_line_no = class_dict[class_name]
            if is_integer_in_range(
                involved_api_line_and_func_line_list,
                st_line_no,
                ed_line_no,
            ):
                additional_involved_lines.append(st_line_no)
        involved_api_line_and_func_line_list.extend(additional_involved_lines)
        involved_api_line_and_func_line_list = sorted(
            list(set(involved_api_line_and_func_line_list))
        )

        additional_line_list = list(
            set(fully_involved_line_list) - set(involved_api_line_and_func_line_list)
        )
        additional_line_number = min(
            max(0, parse_total_lines_threshold - len(involved_api_line_and_func_line_list)),
            len(additional_line_list),
        )
        if additional_line_number > 0:
            involved_api_line_and_func_line_list.extend(
                random.sample(additional_line_list, additional_line_number)
            )
        involved_api_line_and_func_line_list = sorted(
            list(set(involved_api_line_and_func_line_list))
        )

        inspiration_text, _, _ = get_inspiration_text(
            code_line_list, involved_api_line_and_func_line_list
        )
        inspiration_list.append(inspiration_text)

    return inspiration_list, syntax_error


def parse_args():
    parser = argparse.ArgumentParser(
        description="Read one Python file and print '\\n'.join(inspiration_list)."
    )
    parser.add_argument("--py_file", type=str, required=True)
    parser.add_argument("--matplotlib_schema_dir", type=str, required=True)
    parser.add_argument("--parse_total_lines_threshold", type=int, required=True)
    return parser.parse_args()


def main():
    args = parse_args()

    if not os.path.isfile(args.py_file):
        raise FileNotFoundError(f"Input file does not exist: {args.py_file}")

    matplotlib_schema_dict = load_matplotlib_schema(args.matplotlib_schema_dir)

    matplotlib_func_set = set()
    for version in matplotlib_schema_dict:
        for func_name in matplotlib_schema_dict[version]:
            matplotlib_func_set.add(func_name)

    with open(args.py_file, "r", encoding="utf-8") as f:
        code_text = f.read()

    inspiration_list, _ = extract_inspiration_list_from_code(
        code_text=code_text,
        parse_total_lines_threshold=args.parse_total_lines_threshold,
        matplotlib_func_set=matplotlib_func_set,
    )

    print("\n".join(inspiration_list))


if __name__ == "__main__":
    main()
