import os
import base64
import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from volcenginesdkarkruntime import Ark

# 配置文件路径
CONFIG_FILE = "config.json"

def load_config():
    """从 config.json 加载配置。"""
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"错误: 配置文件 {CONFIG_FILE} 未找到。请将 config.json.template 复制为 config.json 并填入您的信息。")
    try:
        # 明确指定使用UTF-8编码读取配置文件
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        if "ARK_API_KEY" not in config or not config["ARK_API_KEY"] or config["ARK_API_KEY"] == "YOUR_API_KEY_HERE":
            raise ValueError(f"错误: 请在 {CONFIG_FILE} 中配置您的 ARK_API_KEY。")
        
        # 确保关键字段存在，如果不存在则使用默认值
        defaults = {
            "PROMPT": "请对比分析这两张图片，总结它们之间的核心差异和共同点。",
            "MAX_WORKERS": 5,
            "INPUT_PRICE_PER_1K_TOKENS": 0.0030,
            "OUTPUT_PRICE_PER_1K_TOKENS": 0.0090
        }
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
            
        return config
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"错误: {CONFIG_FILE} 格式不正确。 {e}")

def estimate_cost(usage, config):
    """根据token用量和单价估算费用"""
    if not usage:
        return 0.0, "无用量信息"
    
    prompt_tokens = usage.prompt_tokens
    completion_tokens = usage.completion_tokens
    
    input_cost = (prompt_tokens / 1000) * config.get("INPUT_PRICE_PER_1K_TOKENS", 0.0030)
    output_cost = (completion_tokens / 1000) * config.get("OUTPUT_PRICE_PER_1K_TOKENS", 0.0090)
    
    total_cost = input_cost + output_cost
    
    cost_info = (
        f"费用: ¥{total_cost:.6f} "
        f"(输入: {prompt_tokens} tokens, 输出: {completion_tokens} tokens)"
    )
    return total_cost, cost_info

# 每次都创建新的客户端，确保使用最新的配置
def get_client():
    """获取Ark客户端，每次都创建新实例以确保使用最新配置。"""
    config = load_config()
    api_key = config.get("ARK_API_KEY")
    base_url = config.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    
    return Ark(
        base_url=base_url,
        api_key=api_key,
    )

def analyze_image_pair_task(image_path1, image_path2, model_id, prompt):
    """
    在单个线程中分析一对图片。这是一个阻塞函数。
    它会返回一个包含分析结果、费用和日志信息的元组。
    """
    ark_client = get_client()
    config = load_config()

    base64_image1 = encode_image_to_base64(image_path1)
    base64_image2 = encode_image_to_base64(image_path2)

    image_format1 = get_image_format(image_path1)
    image_format2 = get_image_format(image_path2)
    
    response = ark_client.chat.completions.create(
        model=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    { "type": "text", "text": prompt },
                    { "type": "image_url", "image_url": { "url": f"data:image/{image_format1};base64,{base64_image1}" }},
                    { "type": "image_url", "image_url": { "url": f"data:image/{image_format2};base64,{base64_image2}" }},
                ],
            }
        ],
        extra_headers={'x-is-encrypted': 'true'},
    )
    
    total_cost, cost_info = estimate_cost(response.usage, config)
    content = response.choices[0].message.content
    
    return content, total_cost, cost_info

# 支持的图片格式
SUPPORTED_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')

def get_image_format(file_path):
    """获取图片格式"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.jpg', '.jpeg']:
        return 'jpeg'
    return ext[1:]

def encode_image_to_base64(image_path):
    """将图片文件编码为Base64字符串。如果失败则抛出IOError。"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except IOError as e:
        # 重新抛出异常，以便上层捕获
        raise IOError(f"无法读取图片文件 {image_path}: {e}") from e

def process_folders(folder1, folder2, model_id, prompt=None, max_workers=5):
    """
    使用多线程处理两个文件夹中的图片对。
    """
    config = load_config()
    if prompt is None:
        prompt = config.get("PROMPT", "请对比分析这两张图片，总结它们之间的核心差异和共同点。")
    
    yield f"开始多线程处理... 最大线程数: {max_workers}"
    yield f"使用提示词: {prompt}"

    # 1. 收集所有待处理的图片对
    folder2_images = {}
    for filename2 in os.listdir(folder2):
        if filename2.lower().endswith(SUPPORTED_EXTENSIONS):
            prefix = os.path.splitext(filename2)[0]
            folder2_images[prefix] = os.path.join(folder2, filename2)

    image_pairs_to_process = {}
    for filename1 in os.listdir(folder1):
        if not filename1.lower().endswith(SUPPORTED_EXTENSIONS):
            continue
        prefix1 = os.path.splitext(filename1)[0]
        if prefix1 in folder2_images:
            image_pairs_to_process[prefix1] = (os.path.join(folder1, filename1), folder2_images[prefix1])
    
    if not image_pairs_to_process:
        yield "未找到任何匹配的图片对进行处理。"
        return

    yield f"共找到 {len(image_pairs_to_process)} 对匹配的图片，开始提交分析任务..."

    # 2. 在线程池中执行任务
    processed_count = 0
    total_estimated_cost = 0.0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_prefix = {
            executor.submit(analyze_image_pair_task, path1, path2, model_id, prompt): prefix
            for prefix, (path1, path2) in image_pairs_to_process.items()
        }

        # 3. 任务完成后，处理结果
        for future in as_completed(future_to_prefix):
            prefix = future_to_prefix[future]
            try:
                analysis_result, cost, cost_info = future.result()
                total_estimated_cost += cost
                
                output_txt_path = os.path.join(folder2, f"{prefix}.txt")
                file_exists = os.path.exists(output_txt_path)
                
                with open(output_txt_path, 'w', encoding='utf-8') as f:
                    f.write(analysis_result)
                
                log_message = ""
                if file_exists:
                    log_message = f"[{prefix}] 分析完成，已替换现有文件: {os.path.basename(output_txt_path)}"
                else:
                    log_message = f"[{prefix}] 分析完成，已保存到新文件: {os.path.basename(output_txt_path)}"
                
                yield f"{log_message} | {cost_info}"
                processed_count += 1

            except Exception as exc:
                yield f"[{prefix}] 处理时发生错误: {exc}"
    
    yield f"-------------------- 处理完成 --------------------"
    yield f"共成功处理了 {processed_count} / {len(image_pairs_to_process)} 对图片。"
    yield f"总预估费用: ¥{total_estimated_cost:.6f}"

def main():
    parser = argparse.ArgumentParser(description="使用豆包API分析两文件夹中的成对图片。")
    parser.add_argument("folder1", help="第一个图片文件夹的路径。")
    parser.add_argument("folder2", help="第二个图片文件夹的路径，分析结果也将保存在此。")

    # 尝试从配置文件加载默认值
    try:
        config = load_config()
        default_model = config.get("MODEL_ID", "ep-20250705181415-gkgwc")
        default_prompt = config.get("PROMPT", "请对比分析这两张图片，总结它们之间的核心差异和共同点。")
        default_workers = config.get("MAX_WORKERS", 5)
    except (FileNotFoundError, ValueError) as e:
        print(f"警告: 加载配置文件失败 ({e})，将使用默认值。")
        default_model = "ep-20250705181415-gkgwc"
        default_prompt = "请对比分析这两张图片，总结它们之间的核心差异和共同点。"
        default_workers = 5

    parser.add_argument(
        "--model",
        default=default_model,
        help=f"指定方舟推理接入点 ID (默认为: {default_model})。"
    )
    
    parser.add_argument(
        "--prompt",
        default=default_prompt,
        help=f"指定发送给API的提示词 (默认为: {default_prompt})。"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=default_workers,
        help=f"指定最大并发线程数 (默认为: {default_workers})。"
    )

    args = parser.parse_args()

    # 检查文件夹是否存在
    if not os.path.isdir(args.folder1):
        print(f"错误: 文件夹 '{args.folder1}' 不存在。")
        return
    if not os.path.isdir(args.folder2):
        print(f"错误: 文件夹 '{args.folder2}' 不存在。")
        return
    
    # 命令行版本保留 print，并捕获API Key异常
    try:
        for log in process_folders(args.folder1, args.folder2, args.model, args.prompt, args.workers):
            print(log)
    except (FileNotFoundError, ValueError) as e:
        print(e)

if __name__ == "__main__":
    main() 