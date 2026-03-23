# Chart2Code53: A Large-Scale Diverse and Complex Dataset for Enhancing Chart-to-Code Generation
<img width="1196" height="686" alt="图片" src="https://github.com/user-attachments/assets/622140f8-7875-4090-8dfe-f0b397a34233" />

## Model Checkpoint
You can download our best model-checkpoint from [Hugging Face](https://huggingface.co/nth2000/Chart2Code53-trained_model). The model is trained with Qwen2-VL.

## Chart2Code53 Dataset
Please download the dataset from the [huggingface](https://huggingface.co/datasets/nth2000/Chart2Code53-training_dataset).
Each dataset sample is a jsonl dict containing:

```python
{
  "instruction": "Redraw the given chart as python code",
  "output": \[plotting code\]
}
```

## Synthesize Pipelines
The full synthesize pipelines are already shown in the figure.
- For code-based pipeline, given a python script which has matplotlib statement, you should first run the following script to get plotting-related statement and then give the output statements to GPT4o to synthesize the full plotting code:
 ```python
 ```
- For image-based pipeline, just give the figure to GPT4o to synthesize the plotting code.

## Model Performance
- Model finetuned on our chart2code53 dataset achieve great performance (till 2025.06)
<img width="980" height="603" alt="图片" src="https://github.com/user-attachments/assets/11d414dc-8617-496b-bb3c-d359d16d607e" />

## Qualitative Samples
<img width="987" height="582" alt="图片" src="https://github.com/user-attachments/assets/62cd4ecc-3472-4828-83ec-5894df8c61b3" />

## Acknowledgements
The code is partly based on the [Text-to-vis](https://aclanthology.org/2024.emnlp-main.423/). Thanks to the greate work!

## Contact info
If you have any questions or issues, feel free to contact thniu@ir.hit.edu.cn 
