from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments


PERSONALITY = "formal"
BASE_MODEL = "unsloth/Qwen2.5-0.5B-Instruct"
MAX_SEQ_LENGTH = 512
LORA_RANK = 16

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = BASE_MODEL,
    max_seq_length = MAX_SEQ_LENGTH,
    dtype = None,
    load_in_4bit = True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r = LORA_RANK,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha = LORA_RANK,
    lora_dropout = 0,
    bias = "none",
    use_gradient_checkpointing = "unsloth",
    random_state = 42,
)


dataset = load_dataset(
    "json", 
    data_files = f"data/{PERSONALITY}.jsonl", 
    split = "train"
    )

def format_example(example):
    text = tokenizer.apply_chat_template(
        example["messages"],
        tokenize = False,
        add_generation_prompt = False,
    )
    return {"text": text}

dataset = dataset.map(format_example)


training_args = TrainingArguments(
    output_dir = f"outputs/{PERSONALITY}",
    per_device_train_batch_size = 4,
    gradient_accumulation_steps = 4,
    warmup_steps = 5,
    num_train_epochs = 3,
    learning_rate = 2e-4,
    logging_steps =5,
    optim = "adamw_8bit",
    weight_decay = 0.01,
    lr_scheduler_type = "linear",
    seed = 42,
    bf16 = True,
    save_strategy = "no",
    report_to = "none",
)

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = MAX_SEQ_LENGTH,
    args = training_args,
)

trainer.train()
model.save_pretrained(f"adapters/{PERSONALITY}")
tokenizer.save_pretrained(f"adapters/{PERSONALITY}")

