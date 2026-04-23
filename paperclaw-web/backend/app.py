#!/usr/bin/env python3
"""
PaperClaw Web Backend API
提供REST API接口用于前端控制PaperClaw流水线
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import json
import os
import threading
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 全局状态
current_run = None
recent_runs = []
running_processes = {}  # 存储运行中的进程: {run_id: process}
ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "artifacts"

# Provider 配置映射
PROVIDER_CONFIG = {
    "deepseek": {"provider": "deepseek", "api_key_env": "DEEPSEEK_API_KEY"},
    "openai": {"provider": "openai", "api_key_env": "OPENAI_API_KEY"},
    "anthropic": {"provider": "anthropic", "api_key_env": "ANTHROPIC_API_KEY"},
    "openrouter": {"provider": "openrouter", "api_key_env": "OPENROUTER_API_KEY"},
    "novita": {"provider": "novita", "api_key_env": "NOVITA_API_KEY"},
    "qwen": {"provider": "qwen", "api_key_env": "DASHSCOPE_API_KEY"},
    "zhipu": {"provider": "zhipu", "api_key_env": "ZHIPU_API_KEY"},
    "ernie": {"provider": "ernie", "api_key_env": "ERNIE_API_KEY"},
    "hunyuan": {"provider": "hunyuan", "api_key_env": "HUNYUAN_API_KEY"},
    "baichuan": {"provider": "baichuan", "api_key_env": "BAICHUAN_API_KEY"},
    "moonshot": {"provider": "moonshot", "api_key_env": "MOONSHOT_API_KEY"},
    "custom": {"provider": "openai-compatible", "api_key_env": "CUSTOM_API_KEY"},
}

# Provider Base URL 配置
PROVIDER_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "openrouter": "https://openrouter.ai/api/v1",
    "novita": "https://api.novita.ai/openai",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "ernie": "https://qianfan.baidubce.com/v2",
    "hunyuan": "https://hunyuan.cloud.tencent.com/v2",
    "baichuan": "https://api.baichuan-ai.com/openai/v1",
    "moonshot": "https://api.moonshot.cn/v1",
}

def run_pipeline(topic: str, api_key: str, provider: str, base_url: str = None, from_stage: str = 'TOPIC_INIT', model: str = None, resume_run_id: str = None):
    """在后台运行PaperClaw流水线

    Args:
        topic: 研究主题
        api_key: API密钥
        provider: LLM提供商
        base_url: 自定义API地址
        from_stage: 起始阶段
        model: 使用的模型
        resume_run_id: 要继续的运行ID（用于断点续传）
    """
    global current_run, running_processes

    # 阶段名称到数字的映射
    STAGE_MAP = {
        'TOPIC_INIT': 1, 'PROBLEM_DECOMPOSE': 2, 'SEARCH_STRATEGY': 3, 'LITERATURE_COLLECT': 4,
        'LITERATURE_SCREEN': 5, 'KNOWLEDGE_EXTRACT': 6, 'SYNTHESIS': 7, 'HYPOTHESIS_GEN': 8,
        'EXPERIMENT_DESIGN': 9, 'CODE_GENERATION': 10, 'RESOURCE_PLANNING': 11, 'EXPERIMENT_RUN': 12,
        'ITERATIVE_REFINE': 13, 'RESULT_ANALYSIS': 14, 'RESEARCH_DECISION': 15, 'PAPER_OUTLINE': 16,
        'PAPER_DRAFT': 17, 'PEER_REVIEW': 18, 'PAPER_REVISION': 19, 'QUALITY_GATE': 20,
        'KNOWLEDGE_ARCHIVE': 21, 'EXPORT_PUBLISH': 22, 'CITATION_VERIFY': 23
    }
    # 数字到阶段名称的反向映射
    STAGE_NUM_TO_NAME = {v: k for k, v in STAGE_MAP.items()}

    # 计算 stage_num
    stage_num = STAGE_MAP.get(from_stage, 1)

    # 如果是继续运行，使用原有的 run_id 和 run_dir
    if resume_run_id:
        run_id = resume_run_id
        run_dir = ARTIFACTS_DIR / run_id
        if not run_dir.exists():
            print(f"[Resume Error] Run directory not found: {run_dir}")
            # 设置错误状态
            current_run = {
                "run_id": run_id,
                "topic": topic,
                "status": "failed",
                "current_stage": 0,
                "total_stages": 23,
                "stage_name": "UNKNOWN",
                "progress": 0.0,
                "error": f"Run directory not found: {run_dir}"
            }
            recent_runs.insert(0, current_run)
            return
        # 继续运行时，从 checkpoint 读取下一阶段
        checkpoint_data = None
        try:
            import json
            checkpoint_file = run_dir / "checkpoint.json"
            if checkpoint_file.exists():
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                # 获取下一阶段的阶段号
                last_completed = checkpoint_data.get("last_completed_stage", 0)
                checkpoint_run_id = checkpoint_data.get("run_id", resume_run_id)
                stage_num = last_completed + 1
                # 检查是否已完成所有阶段
                if stage_num > 23:
                    print(f"[Resume] All stages already completed (last: {last_completed})")
                    current_run = {
                        "run_id": run_id,
                        "topic": topic,
                        "status": "completed",
                        "current_stage": 23,
                        "total_stages": 23,
                        "stage_name": "CITATION_VERIFY",
                        "progress": 100.0
                    }
                    recent_runs.insert(0, current_run)
                    return
                # 更新 from_stage 为下一阶段
                from_stage = STAGE_NUM_TO_NAME.get(stage_num, 'TOPIC_INIT')
                print(f"[Resume] Found checkpoint: run_id={checkpoint_run_id}, last_completed={last_completed}, next={stage_num} ({from_stage})")
        except Exception as e:
            print(f"[Resume] Error reading checkpoint: {e}")
            # 出错时从 stage-1 开始
            stage_num = 1
            from_stage = 'TOPIC_INIT'
    else:
        run_id = f"pc-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{hash(topic) % 10000:04x}"

        # 创建运行目录
        run_dir = ARTIFACTS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

    # 如果不是从头开始且不是继续运行，需要复制前序阶段的输出文件
    if from_stage and from_stage != 'TOPIC_INIT' and not resume_run_id:
        # 查找包含完整前序阶段的运行
        source_run = None
        needed_stages = range(1, stage_num)  # 需要 1 到 stage_num-1

        for artifact_dir in sorted(ARTIFACTS_DIR.iterdir(), reverse=True):
            if artifact_dir.is_dir() and artifact_dir.name.startswith("pc-"):
                # 检查是否包含所有必需的阶段
                all_exist = True
                for i in needed_stages:
                    stage_path = artifact_dir / f"stage-{i:02d}"
                    if not stage_path.exists():
                        all_exist = False
                        break
                if all_exist:
                    source_run = artifact_dir
                    break

        if source_run:
            print(f"[Pipeline] Copying artifacts from {source_run.name}")
            # 复制前序阶段的 stage 目录
            for i in needed_stages:
                src_stage = source_run / f"stage-{i:02d}"
                if src_stage.exists():
                    dst_stage = run_dir / f"stage-{i:02d}"
                    import shutil
                    shutil.copytree(src_stage, dst_stage, dirs_exist_ok=True)
                # 也复制带版本的 stage 目录
                for src_stage in source_run.glob(f"stage-{i}_v*"):
                    dst_stage = run_dir / src_stage.name
                    import shutil
                    shutil.copytree(src_stage, dst_stage, dirs_exist_ok=True)
        else:
            print(f"[Pipeline] WARNING: No source run found with stages 1-{stage_num-1}")

    current_run = {
        "run_id": run_id,
        "topic": topic,
        "status": "running",
        "current_stage": stage_num,
        "total_stages": 23,
        "stage_name": from_stage,
        "progress": (stage_num / 23) * 100
    }

    # 获取provider配置
    provider_info = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["deepseek"])

    # 设置环境变量
    env = os.environ.copy()
    env[provider_info["api_key_env"]] = api_key
    env["PYTHONUNBUFFERED"] = "1"  # 禁用 Python 输出缓冲，确保实时输出

    # 确定base_url
    if base_url:
        final_base_url = base_url
        final_provider = "openai-compatible"
    else:
        final_base_url = PROVIDER_BASE_URLS.get(provider, "https://api.deepseek.com/v1")
        final_provider = provider

    # 读取并更新配置文件
    config_path = Path(__file__).parent.parent.parent / "config.paperclaw.yaml"
    import yaml

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 更新LLM配置
    config['llm']['provider'] = final_provider
    config['llm']['base_url'] = final_base_url
    config['llm']['api_key'] = api_key
    config['llm']['api_key_env'] = provider_info["api_key_env"]  # 同步 api_key_env

    # 根据provider设置默认模型（如果用户没有指定则使用默认）
    default_models = {
        "deepseek": "deepseek-chat",
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-20241022",
        "openrouter": "anthropic/claude-3.5-sonnet",
        "novita": "anthropic/claude-3.5-sonnet-20241022",
        "qwen": "qwen-plus",
        "zhipu": "glm-4-plus",
        "ernie": "ernie-4.0-8k",
        "hunyuan": "hunyuan-pro",
        "baichuan": "baichuan4",
        "moonshot": "moonshot-v1-8k",
        "openai-compatible": "gpt-4o",
    }

    # 使用用户选择的模型，如果没有则使用默认模型
    selected_model = model if model else default_models.get(final_provider, "gpt-4o")
    config['llm']['primary_model'] = selected_model

    # 保存临时配置（运行时使用）
    temp_config_path = Path(__file__).parent.parent.parent / "config.paperclaw.temp.yaml"
    with open(temp_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)

    # 同时更新主配置文件（下次运行保持用户选择）
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
    except Exception as e:
        print(f"[Config] Warning: Failed to update main config: {e}")

    # 项目根目录
    project_root = Path(__file__).parent.parent.parent

    # 运行PaperClaw - 使用 Python 模块方式，避免路径问题
    python_exe = sys.executable  # 使用当前 Python 解释器

    cmd = [
        python_exe,
        "-u",  # 无缓冲模式，确保实时输出
        "-m", "researchclaw.cli",
        "run",
        "--config", str(temp_config_path),
        "--topic", topic,
        "--output", str(run_dir),  # 指定输出目录，包含已复制的 artifacts
        "--auto-approve",
        "--skip-noncritical-stage",
        "--skip-preflight"  # 跳过预检，避免挂起
    ]

    # 添加起始阶段参数
    if from_stage and from_stage != 'TOPIC_INIT':
        cmd.extend(["--from-stage", from_stage])

    # 日志文件路径
    log_file = ARTIFACTS_DIR / run_id / "paperclaw_output.log"
    ARTIFACTS_DIR / run_id / "paperclaw_output.log"

    try:
        # 运行PaperClaw - 使用 Python 模块方式，避免路径问题
        process = subprocess.Popen(
            cmd,
            cwd=str(Path(__file__).parent.parent.parent),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1  # 行缓冲
        )

        # 保存进程引用，用于后续停止
        running_processes[run_id] = process

        # 使用文本解码
        import io
        stdout_reader = io.TextIOWrapper(process.stdout, encoding='utf-8', errors='replace')

        # 监控进程输出
        with open(log_file, 'w', encoding='utf-8') as log_f:
            for line in stdout_reader:
                line = line.strip()
                if line:
                    print(f"[PaperClaw] {line}")
                    log_f.write(line + '\n')
                    log_f.flush()

                    # 解析阶段进度 - 格式: [run_id] Stage XX/23 STAGE_NAME — running...
                    if "Stage" in line and "/" in line:
                        try:
                            stage_part = line.split("Stage")[1].strip()
                            stage_info = stage_part.split()[0]  # XX/23

                            if "/" in stage_info:
                                current, total = map(int, stage_info.split("/"))
                                current_run["current_stage"] = current
                                current_run["total_stages"] = total
                                current_run["progress"] = (current / total) * 100

                                # 提取阶段名称
                                remaining = stage_part.split(stage_info)[1].strip()
                                stage_name = remaining.split()[0] if remaining else "UNKNOWN"
                                current_run["stage_name"] = stage_name
                        except Exception:
                            pass

        process.wait()

        if process.returncode == 0:
            current_run["status"] = "completed"
            current_run["progress"] = 100
        else:
            current_run["status"] = "failed"

        recent_runs.insert(0, current_run.copy())
        if len(recent_runs) > 10:
            recent_runs.pop()

    except Exception as e:
        print(f"[Pipeline Error] {e}")
        if current_run:
            current_run["status"] = "failed"
            recent_runs.insert(0, current_run.copy())
    finally:
        # 清理进程引用
        if run_id in running_processes:
            del running_processes[run_id]

# 阶段名称映射（数字 -> 名称）
STAGE_NUM_TO_NAME = {
    1: 'TOPIC_INIT', 2: 'PROBLEM_DECOMPOSE', 3: 'SEARCH_STRATEGY',
    4: 'LITERATURE_COLLECT', 5: 'LITERATURE_SCREEN', 6: 'KNOWLEDGE_EXTRACT',
    7: 'SYNTHESIS', 8: 'HYPOTHESIS_GEN', 9: 'EXPERIMENT_DESIGN',
    10: 'CODE_GENERATION', 11: 'RESOURCE_PLANNING', 12: 'EXPERIMENT_RUN',
    13: 'ITERATIVE_REFINE', 14: 'RESULT_ANALYSIS', 15: 'RESEARCH_DECISION',
    16: 'PAPER_OUTLINE', 17: 'PAPER_DRAFT', 18: 'PEER_REVIEW',
    19: 'PAPER_REVISION', 20: 'QUALITY_GATE', 21: 'KNOWLEDGE_ARCHIVE',
    22: 'EXPORT_PUBLISH', 23: 'CITATION_VERIFY'
}

def scan_artifacts_for_runs():
    """扫描artifacts目录，获取所有运行的真实状态"""
    runs = []

    if not ARTIFACTS_DIR.exists():
        return runs

    for run_dir in sorted(ARTIFACTS_DIR.iterdir(), reverse=True):
        if not run_dir.is_dir() or not run_dir.name.startswith("pc-"):
            continue

        run_id = run_dir.name
        checkpoint_file = run_dir / "checkpoint.json"
        heartbeat_file = run_dir / "heartbeat.json"
        log_file = run_dir / "paperclaw_output.log"

        # 默认状态
        run_info = {
            "run_id": run_id,
            "topic": "Unknown Research",
            "status": "failed",
            "current_stage": 0,
            "total_stages": 23,
            "stage_name": "UNKNOWN",
            "progress": 0.0
        }

        # 从checkpoint获取完成阶段
        if checkpoint_file.exists():
            try:
                import json
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                last_completed = checkpoint.get("last_completed_stage", 0)
                stage_name = checkpoint.get("last_completed_name", "UNKNOWN")

                # 判断状态
                if last_completed >= 23:
                    run_info["status"] = "completed"
                    run_info["current_stage"] = 23
                    run_info["stage_name"] = "CITATION_VERIFY"
                    run_info["progress"] = 100.0
                else:
                    # 检查是否有正在运行的迹象
                    # 如果当前正在运行这个run，则状态为running
                    if current_run and current_run.get("run_id") == run_id:
                        run_info["status"] = "running"
                        run_info["current_stage"] = current_run.get("current_stage", last_completed + 1)
                        run_info["stage_name"] = current_run.get("stage_name", STAGE_NUM_TO_NAME.get(last_completed + 1, "UNKNOWN"))
                        run_info["progress"] = current_run.get("progress", (last_completed + 1) / 23 * 100)
                    else:
                        # 从heartbeat或日志判断是否还在运行
                        is_running = False
                        if heartbeat_file.exists():
                            try:
                                import json
                                with open(heartbeat_file, 'r', encoding='utf-8') as f:
                                    heartbeat = json.load(f)
                                # 检查心跳时间（最近5分钟内有更新则认为可能还在运行）
                                from datetime import datetime, timedelta
                                import time
                                heartbeat_time = heartbeat.get("timestamp", "")
                                if heartbeat_time:
                                    try:
                                        # 尝试解析时间戳
                                        hb_dt = datetime.fromisoformat(heartbeat_time.replace('Z', '+00:00'))
                                        if datetime.now(hb_dt.tzinfo) - hb_dt < timedelta(minutes=5):
                                            # 最近有活动，可能是运行中的
                                            # 但如果没有在current_run中，说明后端重启过
                                            # 这种情况下标记为failed，可以继续
                                            is_running = False
                                    except:
                                        pass
                            except:
                                pass

                        if not is_running:
                            run_info["status"] = "failed"
                            run_info["current_stage"] = last_completed
                            run_info["stage_name"] = stage_name
                            run_info["progress"] = (last_completed / 23) * 100

                # 尝试获取topic
                try:
                    summary_file = run_dir / "pipeline_summary.json"
                    if summary_file.exists():
                        with open(summary_file, 'r', encoding='utf-8') as f:
                            summary = json.load(f)
                        run_info["topic"] = summary.get("topic", run_info["topic"])
                except:
                    pass

            except Exception as e:
                print(f"[Scan] Error parsing checkpoint for {run_id}: {e}")

        runs.append(run_info)

    return runs


@app.route('/api/status', methods=['GET'])
def get_status():
    """获取当前运行状态"""
    # 从artifacts目录扫描所有运行
    all_runs = scan_artifacts_for_runs()

    # 合并当前运行信息（如果正在运行）
    if current_run:
        # 更新all_runs中对应的run
        for run in all_runs:
            if run["run_id"] == current_run["run_id"]:
                run.update(current_run)
                break
        else:
            # 如果不在列表中，添加到前面
            all_runs.insert(0, current_run)

    return jsonify({
        "current_run": current_run,
        "recent_runs": all_runs[:50]  # 返回最多50个运行
    })


@app.route('/api/runs', methods=['GET'])
def get_all_runs():
    """获取所有历史运行记录（从artifacts目录扫描）"""
    runs = scan_artifacts_for_runs()
    return jsonify({
        "runs": runs[:100],  # 最多返回100个
        "total": len(runs)
    })

@app.route('/api/run', methods=['POST'])
def start_run():
    """启动新的研究流水线"""
    data = request.json
    topic = data.get('topic')
    api_key = data.get('api_key')
    provider = data.get('provider', 'deepseek')
    model = data.get('model')  # 用户选择的模型
    base_url = data.get('base_url')  # 自定义 base_url
    from_stage = data.get('from_stage')  # 起始阶段

    if not topic or not api_key:
        return jsonify({"error": "Missing topic or api_key"}), 400

    # 在后台线程运行
    thread = threading.Thread(
        target=run_pipeline,
        args=(topic, api_key, provider, base_url, from_stage, model)
    )
    thread.daemon = True
    thread.start()

    return jsonify({"run": current_run})

@app.route('/api/results/<run_id>', methods=['GET'])
def get_results(run_id):
    """获取指定运行的结果"""
    run_dir = ARTIFACTS_DIR / run_id / "deliverables"
    
    if not run_dir.exists():
        return jsonify({"error": "Run not found"}), 404
    
    files = []
    for file in run_dir.iterdir():
        if file.is_file():
            files.append({
                "name": file.name,
                "size": file.stat().st_size
            })
    
    # 读取论文预览
    paper_preview = None
    paper_file = run_dir / "paper_draft.md"
    if paper_file.exists():
        with open(paper_file, 'r', encoding='utf-8') as f:
            paper_preview = f.read()[:2000]  # 前2000字符
    
    return jsonify({
        "files": files,
        "paper_preview": paper_preview
    })

@app.route('/api/download/<run_id>/<filename>', methods=['GET'])
def download_file(run_id, filename):
    """下载指定文件"""
    file_path = ARTIFACTS_DIR / run_id / "deliverables" / filename

    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    return send_file(file_path, as_attachment=True)

@app.route('/api/logs/<run_id>/<int:stage_num>', methods=['GET'])
def get_stage_log(run_id, stage_num):
    """获取指定运行指定阶段的日志"""
    log_file = ARTIFACTS_DIR / run_id / "paperclaw_output.log"

    if not log_file.exists():
        return jsonify({"error": "Log file not found"}), 404

    try:
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        # 从日志中提取该阶段的日志
        # 阶段格式: [run_id] Stage XX/23 STAGE_NAME
        stage_markers = []
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if f"Stage {stage_num}/" in line or f"Stage {stage_num} " in line:
                stage_markers.append(i)

        if not stage_markers:
            # 如果找不到该阶段，返回最后200行
            log_content = '\n'.join(lines[-200:])
        else:
            start_idx = stage_markers[0]
            # 找到下一个阶段的开始位置
            end_idx = len(lines)
            for i in range(start_idx + 1, len(lines)):
                if "Stage " in lines[i] and "/" in lines[i]:
                    end_idx = i
                    break
            log_content = '\n'.join(lines[start_idx:end_idx])

        return jsonify({
            "run_id": run_id,
            "stage_num": stage_num,
            "log": log_content
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats/<run_id>', methods=['GET'])
def get_run_stats(run_id):
    """获取指定运行的模型使用统计"""
    run_dir = ARTIFACTS_DIR / run_id

    if not run_dir.exists():
        return jsonify({"error": "Run not found"}), 404

    # 默认统计信息
    stats = {
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "api_calls": 0,
        "current_model": "-",
        "context_length": 0,
        "tools_used": [],
        "estimated_cost": 0.0
    }

    try:
        # 尝试从日志文件解析 token 使用情况
        log_file = run_dir / "paperclaw_output.log"
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                # 统计 API 调用次数（基于阶段标记）
                import re
                stage_matches = re.findall(rf'\[{re.escape(run_id)}\] Stage \d+/23', content)
                stats["api_calls"] = len(stage_matches)

        # 尝试读取 heartbeat.json 获取更多信息
        heartbeat_file = run_dir / "heartbeat.json"
        if heartbeat_file.exists():
            import json
            with open(heartbeat_file, 'r', encoding='utf-8') as f:
                heartbeat = json.load(f)
                stats["api_calls"] = heartbeat.get("last_stage", 0)

        # 尝试读取 checkpoint.json
        checkpoint_file = run_dir / "checkpoint.json"
        if checkpoint_file.exists():
            import json
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
                stats["api_calls"] = checkpoint.get("last_completed_stage", 0)

        # 从配置获取当前模型信息
        config_path = Path(__file__).parent.parent.parent / "config.paperclaw.yaml"
        if config_path.exists():
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                stats["current_model"] = config.get('llm', {}).get('primary_model', '-')

        # 根据模型和 token 数估算成本（智谱 GLM 价格）
        model = stats["current_model"]
        if "glm-4-plus" in model.lower() or "glm-4" in model.lower():
            # GLM-4 Plus: 输入 ¥0.05/千tokens, 输出 ¥0.5/千tokens
            # 由于我们暂时无法准确获取输入输出 token，使用平均价格估算
            stats["estimated_cost"] = stats["api_calls"] * 0.01  # 每次调用约 ¥0.01

        stats["context_length"] = 128000  # GLM-4 Plus 默认上下文长度
        stats["total_tokens"] = stats["api_calls"] * 2000  # 估算：每次调用约 2000 tokens
        stats["prompt_tokens"] = int(stats["total_tokens"] * 0.7)
        stats["completion_tokens"] = int(stats["total_tokens"] * 0.3)

        # 工具列表（根据阶段推断）
        tools = []
        if stats["api_calls"] >= 1:
            tools.append("literature_search")
        if stats["api_calls"] >= 6:
            tools.append("knowledge_extract")
        if stats["api_calls"] >= 10:
            tools.append("code_generation")
        if stats["api_calls"] >= 12:
            tools.append("experiment_runner")
        if stats["api_calls"] >= 16:
            tools.append("paper_writer")

        stats["tools_used"] = tools

        return jsonify(stats)
    except Exception as e:
        # 返回默认统计
        return jsonify(stats)


@app.route('/api/runs/<run_id>', methods=['DELETE'])
def delete_run(run_id):
    """删除指定运行的所有文件（日志、artifacts等）"""
    global current_run, recent_runs

    run_dir = ARTIFACTS_DIR / run_id

    if not run_dir.exists():
        return jsonify({"error": "Run not found"}), 404

    try:
        import shutil

        # 检查是否是当前正在运行的任务
        is_current_run = current_run and current_run.get('run_id') == run_id

        if is_current_run:
            # 如果正在运行，发出警告并返回
            return jsonify({
                "error": "Cannot delete running task. Please wait for it to complete or stop it first.",
                "is_running": True
            }), 400

        # 删除 artifacts 目录
        shutil.rmtree(run_dir)
        print(f"[Delete] Deleted run directory: {run_dir}")

        # 从 recent_runs 内存中移除
        recent_runs = [r for r in recent_runs if r.get('run_id') != run_id]

        # 如果是 current_run（虽然上面已经检查），清空它
        if current_run and current_run.get('run_id') == run_id:
            current_run = None
            print(f"[Delete] Cleared current_run: {run_id}")

        return jsonify({
            "success": True,
            "message": f"Run {run_id} deleted successfully",
            "run_id": run_id
        })
    except Exception as e:
        print(f"[Delete Error] Failed to delete {run_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/runs/bulk-delete', methods=['POST'])
def bulk_delete_runs():
    """批量删除运行记录"""
    global current_run, recent_runs

    data = request.json
    run_ids = data.get('run_ids', [])

    if not run_ids:
        return jsonify({"error": "No run IDs provided"}), 400

    print(f"[Bulk Delete] Deleting {len(run_ids)} runs...", flush=True)

    results = {
        "success": [],
        "failed": [],
        "running": []
    }

    import shutil

    for run_id in run_ids:
        run_dir = ARTIFACTS_DIR / run_id

        # 检查是否正在运行
        if current_run and current_run.get('run_id') == run_id:
            results["running"].append(run_id)
            continue

        if not run_dir.exists():
            results["failed"].append({"run_id": run_id, "error": "Run not found"})
            continue

        try:
            # 删除 artifacts 目录
            shutil.rmtree(run_dir)

            # 从 recent_runs 内存中移除
            recent_runs = [r for r in recent_runs if r.get('run_id') != run_id]

            results["success"].append(run_id)
            print(f"[Bulk Delete] ✓ {run_id}", flush=True)
        except Exception as e:
            results["failed"].append({"run_id": run_id, "error": str(e)})
            print(f"[Bulk Delete] ✗ {run_id}: {e}", flush=True)

    # 返回详细结果
    return jsonify({
        "success": True,
        "message": f"Bulk delete completed: {len(results['success'])} succeeded, {len(results['failed'])} failed, {len(results['running'])} skipped (running)",
        "results": results
    })


@app.route('/api/runs/<run_id>/stop', methods=['POST'])
def stop_run(run_id):
    """停止正在运行的任务"""
    global current_run, running_processes

    if not current_run or current_run.get('run_id') != run_id:
        return jsonify({"error": "Task is not running"}), 400

    try:
        # 保存当前运行信息
        run_info = current_run.copy()

        # 尝试终止进程
        process = running_processes.get(run_id)
        if process:
            print(f"[Stop] Terminating process for run {run_id}")
            try:
                process.terminate()
                # 等待最多5秒让进程优雅退出
                try:
                    process.wait(timeout=5)
                except:
                    # 如果进程没有退出，强制杀死
                    print(f"[Stop] Force killing process for run {run_id}")
                    process.kill()
                    process.wait(timeout=2)
            except Exception as e:
                print(f"[Stop] Error terminating process: {e}")
                # 即使终止失败，也继续清理状态
        else:
            print(f"[Stop] No process found for run {run_id}, only clearing state")

        # 清空当前运行状态
        current_run = None

        print(f"[Stop] Run {run_id} stopped successfully")

        return jsonify({
            "success": True,
            "message": f"任务已暂停，可以稍后继续执行",
            "run": run_info
        })
    except Exception as e:
        print(f"[Stop Error] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/runs/<run_id>/resume', methods=['POST'])
def resume_run(run_id):
    """从断点继续运行指定的研究任务"""
    global current_run

    run_dir = ARTIFACTS_DIR / run_id

    if not run_dir.exists():
        return jsonify({"error": "Run not found"}), 404

    # 读取 checkpoint 获取断点信息
    checkpoint_file = run_dir / "checkpoint.json"
    if not checkpoint_file.exists():
        return jsonify({"error": "No checkpoint found, cannot resume"}), 400

    try:
        import json
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)

        # 检查是否有正在运行的进程
        if current_run and current_run.get('run_id') == run_id:
            return jsonify({"error": "This run is already active"}), 400

        if current_run:
            return jsonify({"error": f"Another run is in progress: {current_run.get('run_id')}"}), 400

        # 获取配置信息
        topic = "Resumed Research"
        last_completed_stage = checkpoint.get("last_completed_stage", 0)

        # 尝试从 pipeline_summary.json 获取原始主题
        summary_file = run_dir / "pipeline_summary.json"
        if summary_file.exists():
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary = json.load(f)
                topic = summary.get("topic", topic)
            except:
                pass

        # 使用当前配置文件获取 API key
        config_path = Path(__file__).parent.parent.parent / "config.paperclaw.yaml"
        if not config_path.exists():
            return jsonify({"error": "Configuration file not found"}), 400

        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        api_key = config.get('llm', {}).get('api_key', '')
        provider = config.get('llm', {}).get('provider', 'zhipu')
        base_url = config.get('llm', {}).get('base_url', '')
        model = config.get('llm', {}).get('primary_model', 'glm-4-plus')

        if not api_key:
            return jsonify({"error": "No API key found in config"}), 400

        # 计算下一阶段
        next_stage_num = last_completed_stage + 1
        if next_stage_num > 23:
            return jsonify({"error": "All stages already completed"}), 400

        # 获取下一阶段名称
        from_stage = STAGE_NUM_TO_NAME.get(next_stage_num, 'TOPIC_INIT')

        print(f"[Resume] Resuming run {run_id} from stage {next_stage_num} ({from_stage})")
        print(f"[Resume] Last completed: stage {last_completed_stage}, Next: stage {next_stage_num}")

        # 在后台线程运行
        thread = threading.Thread(
            target=run_pipeline,
            args=(topic, api_key, provider, base_url, from_stage, model, run_id)
        )
        thread.daemon = True
        thread.start()

        # 更新 current_run
        next_stage_num = last_completed_stage + 1
        current_run = {
            "run_id": run_id,
            "topic": topic,
            "status": "running",
            "current_stage": next_stage_num,
            "total_stages": 23,
            "stage_name": from_stage,
            "progress": (next_stage_num / 23) * 100
        }

        return jsonify({
            "success": True,
            "run": current_run,
            "message": f"从阶段 {next_stage_num} ({from_stage}) 继续执行"
        })

    except Exception as e:
        print(f"[Resume Error] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Import research mode routes
from routes_research import research_bp
app.register_blueprint(research_bp)

if __name__ == '__main__':
    print("🦞 PaperClaw Web Backend starting...")
    print("📡 API Server: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
