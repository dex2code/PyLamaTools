settings = {

    "log_level": "WARNING",

    "tools_dir": "tools",
    "workspace_dir": "workspace",

    "system_prompt_file": "system_prompt.txt",
    "system_prompt_file_encoding": "utf-8",

    "ollama_url": "http://127.0.0.1:11434",
    "ollama_model": "ornith-1.5:9b",

    "tool_iterations": 128,

    "context_max_tokens": 65536,
    "context_encoding": "cl100k_base",

    "display_thinking": True,
    "display_tool_call": True,
    "display_answer": True,
    "display_content_length": True,

    "model_thinking": True,
    "model_streaming": True,

    "options": {
        "temperature": 0.6,
        "top_k": 20,
        "top_p": 0.95
    }

}
