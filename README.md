# Chart2Code53: A Large-Scale Diverse and Complex Dataset for Enhancing Chart-to-Code Generation
<img width="1196" height="686" alt="图片" src="https://github.com/user-attachments/assets/622140f8-7875-4090-8dfe-f0b397a34233" />

## Model Checkpoint
You can download our best model-checkpoint from [Hugging Face](https://huggingface.co/nth2000/Chart2Code53-trained_model). The model is trained with Qwen2-VL.

## Chart2Code53 Dataset
Please fill in this form to get access to the Chart2Code53 dataset.
Each dataset sample is a jsonl dict containing:

```python
{
  "instruction": "Redraw the given chart as python code",
  "output": \[plotting code\]
}
```

## Synthesize Pipelines

## Model Performance
- Model finetuned on our chart2code53 dataset achieve great performance (till 2025.06)
<img width="980" height="603" alt="图片" src="https://github.com/user-attachments/assets/11d414dc-8617-496b-bb3c-d359d16d607e" />
