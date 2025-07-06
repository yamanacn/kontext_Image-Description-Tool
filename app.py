import gradio as gr
import os
import json
from image_analyzer import process_folders, load_config

# 配置文件路径
CONFIG_FILE = "config.json"
CONFIG_TEMPLATE_FILE = "config.json.template"

# 从配置文件加载配置，如果不存在则使用默认值
def load_config_for_ui():
    """加载配置文件，返回配置字典。如果文件不存在或格式不正确，返回默认值。"""
    default_config = {
        "ARK_API_KEY": "",
        "MODEL_ID": "ep-20250705181415-gkgwc",
        "ARK_BASE_URL": "https://ark.cn-beijing.volces.com/api/v3",
        "PROMPT": "请对比分析这两张图片，总结它们之间的核心差异和共同点。",
        "MAX_WORKERS": 5,
        "INPUT_PRICE_PER_1K_TOKENS": 0.0030,
        "OUTPUT_PRICE_PER_1K_TOKENS": 0.0090
    }
    
    try:
        if os.path.exists(CONFIG_FILE):
            # 明确指定使用UTF-8编码读取配置文件
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 确保所有必要的字段都存在
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        elif os.path.exists(CONFIG_TEMPLATE_FILE):
            # 如果模板存在但配置文件不存在，从模板创建配置
            with open(CONFIG_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                template = json.load(f)
                for key, value in default_config.items():
                    if key not in template:
                        template[key] = value
                # 保存为新的配置文件，使用UTF-8编码
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(template, f, indent=2, ensure_ascii=False)
                return template
        else:
            # 如果两个文件都不存在，创建新的配置文件，使用UTF-8编码
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    except Exception as e:
        print(f"加载配置文件时出错: {e}")
        return default_config

# 保存配置到文件
def save_config(api_key, model_id, base_url, prompt, max_workers, input_price, output_price):
    """将配置保存到 config.json 文件。"""
    config = {
        "ARK_API_KEY": api_key,
        "MODEL_ID": model_id,
        "ARK_BASE_URL": base_url,
        "PROMPT": prompt,
        "MAX_WORKERS": int(max_workers),
        "INPUT_PRICE_PER_1K_TOKENS": float(input_price),
        "OUTPUT_PRICE_PER_1K_TOKENS": float(output_price)
    }
    try:
        # 使用UTF-8编码保存配置文件，并确保中文不被转义
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return f"配置已成功保存到 {CONFIG_FILE}"
    except Exception as e:
        return f"保存配置时出错: {e}"

# 更新配置并保存
def update_config(api_key, model_id, base_url, prompt, max_workers, input_price, output_price):
    result = save_config(api_key, model_id, base_url, prompt, max_workers, input_price, output_price)
    return result

# Gradio 界面调用的主函数
def start_analysis(folder1, folder2, model_id, api_key, base_url, prompt, max_workers, input_price, output_price):
    # 首先保存当前配置
    save_config(api_key, model_id, base_url, prompt, max_workers, input_price, output_price)
    
    if not os.path.isdir(folder1):
        yield f"错误: 文件夹 '{folder1}' 不存在。"
        return
    
    if not os.path.isdir(folder2):
        yield f"错误: 文件夹 '{folder2}' 不存在。"
        return
    
    log_output = ""
    try:
        # 调用核心处理函数，并流式接收日志
        for log in process_folders(folder1, folder2, model_id, prompt, int(max_workers)):
            if log.startswith("总预估费用:"):
                # 在终端打印总费用
                print(log) 
            log_output += log + "\n"
            yield log_output
    except (FileNotFoundError, ValueError) as e:
        # 捕获因缺少API Key或配置文件错误而引发的异常
        yield str(e)

# 加载配置
config = load_config_for_ui()

# 创建 Gradio 界面
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 豆包 API 双图对比分析工具-作者OLDX")
    gr.Markdown("输入两个包含成对图片的文件夹路径，程序将使用多线程并发分析，并将结果保存在第二个文件夹中。")

    with gr.Tabs():
        with gr.TabItem("主面板"):
            with gr.Row():
                folder_input1 = gr.Textbox(label="文件夹 1 路径", placeholder="例如: C:\\Users\\YourUser\\Desktop\\images_a", scale=1)
                folder_input2 = gr.Textbox(label="文件夹 2 路径 (结果也将保存于此)", placeholder="例如: C:\\Users\\YourUser\\Desktop\\images_b", scale=1)

            with gr.Accordion("配置（点击可折叠）", open=True):
                prompt_input = gr.Textbox(
                    label="提示词 (Prompt)",
                    value=config.get("PROMPT", "请对比分析这两张图片，总结它们之间的核心差异和共同点。"),
                    lines=3,
                    info="发送给 API 的提示词，用于指导模型如何分析图片"
                )
                with gr.Row():
                    api_key_input = gr.Textbox(
                        label="API Key",
                        value=config.get("ARK_API_KEY", ""),
                        type="password",
                        info="您的火山方舟 API Key"
                    )
                    model_input = gr.Textbox(
                        label="模型 ID (Model ID)",
                        value=config.get("MODEL_ID", "ep-20250705181415-gkgwc"),
                        info="指定您希望使用的方舟推理接入点 ID"
                    )

                base_url_input = gr.Textbox(
                    label="API 基础 URL",
                    value=config.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
                    info="API 服务的基础 URL，一般无需修改"
                )

                workers_slider = gr.Slider(
                    minimum=1,
                    maximum=8,
                    value=config.get("MAX_WORKERS", 5),
                    step=1,
                    label="最大线程数 (Max Workers)",
                    info="设置同时进行分析的最大任务数。请根据您的网络和机器性能调整。"
                )

                with gr.Row():
                    input_price_input = gr.Number(
                        label="输入价格 (元/千Tokens)",
                        value=config.get("INPUT_PRICE_PER_1K_TOKENS", 0.0030),
                        info="模型输入的计费单价"
                    )
                    output_price_input = gr.Number(
                        label="输出价格 (元/千Tokens)",
                        value=config.get("OUTPUT_PRICE_PER_1K_TOKENS", 0.0090),
                        info="模型输出的计费单价"
                    )

                save_button = gr.Button("仅保存配置", variant="secondary")

            start_button = gr.Button("开始分析", variant="primary")

            output_logs = gr.Textbox(label="分析日志", lines=15, autoscroll=True, interactive=False)

        with gr.TabItem("使用说明"):
            gr.Markdown("""
            ### 使用说明

            #### 如何操作
            1. **输入路径**: 在主面板中，填入两个包含图片的文件夹路径。
            2. **检查配置**: "配置"区域默认展开，您可以在此修改提示词、API Key、线程数等高级设置。
            3. **开始分析**: 点击 "开始分析" 按钮。程序会自动保存当前所有配置并开始执行任务。
            4. **查看结果**: 日志区域会实时显示分析进度。**总预估费用将打印在程序启动的终端窗口中**。分析结果的 `.txt` 文件会保存在 "文件夹 2" 中。

            #### 配置项
            - **提示词**: 指导模型进行分析的指令。
            - **API Key / 模型 ID**: 您的模型凭证和模型标识。
            - **最大线程数**: 并发分析的任务数。**数量并非越多越好**，建议从5-10开始尝试。
            - **价格设置**: Token的单价，用于费用估算。
            - 点击 "仅保存配置" 按钮可以将当前所有设置保存到 `config.json` 文件中，而不启动分析。

            #### 注意事项
            - 日志是并发输出的，顺序可能与任务提交顺序不同，这是正常现象。
            - 预估费用仅供参考，实际费用以服务商账单为准。
            """)

    # 绑定保存配置按钮
    save_button.click(
        fn=update_config,
        inputs=[api_key_input, model_input, base_url_input, prompt_input, workers_slider, input_price_input, output_price_input]
    )

    # 绑定开始分析按钮
    start_button.click(
        fn=start_analysis,
        inputs=[folder_input1, folder_input2, model_input, api_key_input, base_url_input, prompt_input, workers_slider, input_price_input, output_price_input],
        outputs=output_logs
    )

if __name__ == "__main__":
    # 启动 Gradio 应用
    demo.launch(
        server_name="127.0.0.1",
        show_error=True,
        quiet=False
    )