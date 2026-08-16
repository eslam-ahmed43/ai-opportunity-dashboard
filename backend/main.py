import os
import json
import re
import time
import threading
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from github import Github
from openai import OpenAI

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

github = Github(os.getenv("GITHUB_TOKEN")) if os.getenv("GITHUB_TOKEN") else Github()
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

DATA_FILE = "opportunities.json"
SCAN_INTERVAL_HOURS = 5

TARGET_ORGS = [
    "langchain-ai", "mlflow", "gradio-app", "streamlit",
    "run-llama", "wandb", "scikit-learn", "keras-team",
    "huggingface", "microsoft", "google", "openai",
    "pytorch", "ray-project", "chroma-core", "qdrant",
    "unslothai", "mistralai", "ollama", "axolotl-ai",
]

CATEGORY_CONFIG = {
    "missing_model": {
        "title_keywords": ["add support for", "model request", "add tokenizer", "new architecture", "implement paper", "add processor", "add config", "conversion script", "add model", "support for model"],
        "body_keywords": ["arxiv", "paper", "architecture", "tokenizer"],
        "career_weight": 95,
        "label": "Missing Model/Architecture",
        "color": "#6366f1",
    },
    "research_impl": {
        "title_keywords": ["implement paper", "paper implementation", "research implementation", "reproduce paper", "implement arxiv", "add paper"],
        "body_keywords": ["arxiv.org", "arxiv:", "paper:", "reproduce"],
        "career_weight": 95,
        "label": "Research Implementation",
        "color": "#8b5cf6",
    },
    "performance": {
        "title_keywords": ["performance", "slow", "optimize", "speed up", "latency", "throughput", "bottleneck", "oom", "out of memory", "memory usage"],
        "body_keywords": [],
        "career_weight": 85,
        "label": "Performance",
        "color": "#f59e0b",
    },
    "onnx_export": {
        "title_keywords": ["onnx", "tensorrt", "flash attention", "torch.compile", "quantization", "export model"],
        "body_keywords": [],
        "career_weight": 85,
        "label": "ONNX/Export",
        "color": "#10b981",
    },
    "missing_integration": {
        "title_keywords": ["add integration", "add support for", "add provider", "missing provider", "add backend", "add llm", "add embedding"],
        "body_keywords": [],
        "career_weight": 80,
        "label": "Missing Integration",
        "color": "#3b82f6",
    },
    "benchmark": {
        "title_keywords": ["benchmark", "add benchmark", "evaluation", "add evaluation", "leaderboard", "add metrics"],
        "body_keywords": [],
        "career_weight": 80,
        "label": "Benchmark",
        "color": "#ec4899",
    },
    "cuda_triton": {
        "title_keywords": ["cuda kernel", "triton kernel", "gpu optimization", "triton"],
        "body_keywords": ["cuda", "triton", "gpu kernel"],
        "career_weight": 75,
        "label": "CUDA/Triton",
        "color": "#ef4444",
    },
    "documentation": {
        "title_keywords": ["add tutorial", "add example", "add notebook", "missing docs", "add documentation"],
        "body_keywords": [],
        "career_weight": 50,
        "label": "Documentation",
        "color": "#64748b",
    },
}


def detect_category(title, body, labels):
    title_lower = title.lower()
    body_lower = body.lower()
    best_category = "general"
    best_weight = 0
    for cat_id, config in CATEGORY_CONFIG.items():
        title_match = any(kw in title_lower for kw in config["title_keywords"])
        body_match = any(kw in body_lower for kw in config.get("body_keywords", []))
        if title_match or (body_match and config["career_weight"] >= 85):
            if config["career_weight"] > best_weight:
                best_weight = config["career_weight"]
                best_category = cat_id
    return best_category, best_weight


def estimate_difficulty(title, body, labels):
    combined = (title + " " + body).lower()
    labels_lower = [l.lower() for l in labels]
    hard_signals = ["cuda kernel", "triton", "distributed", "deepspeed", "backward pass", "gradient", "race condition", "memory leak"]
    easy_signals = ["good first issue", "good-first-issue", "beginner", "easy", "starter", "documentation", "simple"]
    hard_count = sum(1 for s in hard_signals if s in combined)
    easy_count = sum(1 for s in easy_signals if s in combined or s in labels_lower)
    if hard_count >= 2:
        return "HARD", "3-4 weeks"
    elif hard_count == 1:
        return "MEDIUM-HARD", "1-2 weeks"
    elif easy_count >= 1:
        return "EASY", "1-3 days"
    elif len(body) > 1500:
        return "MEDIUM", "3-7 days"
    else:
        return "EASY-MEDIUM", "2-5 days"


def calculate_score(issue_data):
    score = 0
    score += (issue_data.get("career_weight", 3) / 6) * 35
    score += min(issue_data.get("comments", 0) / 20, 1.0) * 20
    merge = 50
    if issue_data.get("stars", 0) > 50000:
        merge += 15
    if issue_data.get("comments", 0) == 0:
        merge += 15
    elif issue_data.get("comments", 0) < 3:
        merge += 10
    score += min(merge / 100, 1.0) * 25
    score += min(issue_data.get("stars", 0) / 200000, 1.0) * 15
    diff_map = {"EASY": 5, "EASY-MEDIUM": 4, "MEDIUM": 3, "MEDIUM-HARD": 2, "HARD": 1}
    score += diff_map.get(issue_data.get("difficulty", "MEDIUM"), 3)
    return round(score, 1)


def analyze_with_ai(title, body, category):
    try:
        config = CATEGORY_CONFIG.get(category, {})
        response = client.chat.completions.create(
            model="meta/llama-3.1-8b-instruct",
            messages=[
                {
                    "role": "system",
                    "content": "You analyze GitHub issues for AI developers. Return ONLY valid JSON with single-line strings."
                },
                {
                    "role": "user",
                    "content": (
                        f"Analyze this GitHub issue:\n"
                        f"Title: {title}\n"
                        f"Category: {config.get('label', category)}\n"
                        f"Description: {body[:300]}\n\n"
                        "Return ONLY JSON:\n"
                        '{"summary":"one sentence what needs to be done",'
                        '"first_step":"exact first action to take",'
                        '"effort":"estimated time",'
                        '"career_signal":"why this matters for AI jobs"}'
                    )
                }
            ],
            max_completion_tokens=200,
            temperature=0.1
        )
        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        start = content.find("{")
        if start < 0:
            return {}
        json_str = content[start:content.rfind("}")+1]
        try:
            return json.loads(json_str)
        except Exception:
            fixed = re.sub(
                r'("(?:[^"\\]|\\.)*")',
                lambda m: m.group(0).replace('\n', ' '),
                json_str
            )
            try:
                return json.loads(fixed)
            except Exception:
                return {}
    except Exception:
        return {}


def scan_opportunities():
    print(f"\nScanning... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    opportunities = []
    seen_urls = set()
    since_date = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")

    for org in TARGET_ORGS:
        try:
            results = github.search_issues(
                query=f"org:{org} is:issue is:open no:assignee created:>={since_date}",
                sort="comments",
                order="desc"
            )
            count = 0
            for issue in results:
                if count >= 10:
                    break
                if issue.html_url in seen_urls:
                    continue
                if issue.pull_request:
                    continue
                if issue.assignees:
                    continue

                labels = [l.name for l in issue.labels]
                labels_lower = [l.lower() for l in labels]
                if any(s in labels_lower for s in ["status:team-assigned", "has-closing-pr", "wip", "in-progress"]):
                    continue

                body = (issue.body or "")[:600]
                category, career_weight = detect_category(issue.title, body, labels)
                if category == "general":
                    continue

                difficulty, time_est = estimate_difficulty(issue.title, body, labels)

                try:
                    repo = github.get_repo(issue.repository.full_name)
                    stars = repo.stargazers_count
                except Exception:
                    stars = 0

                issue_data = {
                    "title": issue.title,
                    "url": issue.html_url,
                    "repo": issue.repository.full_name,
                    "stars": stars,
                    "labels": labels,
                    "comments": issue.comments,
                    "created_at": issue.created_at.strftime("%Y-%m-%d"),
                    "category": category,
                    "category_label": CATEGORY_CONFIG.get(category, {}).get("label", category),
                    "category_color": CATEGORY_CONFIG.get(category, {}).get("color", "#64748b"),
                    "career_weight": career_weight,
                    "difficulty": difficulty,
                    "time_estimate": time_est,
                    "ai_analysis": {},
                }
                issue_data["score"] = calculate_score(issue_data)

                seen_urls.add(issue.html_url)
                opportunities.append(issue_data)
                count += 1

        except Exception as e:
            if "422" not in str(e) and "403" not in str(e):
                print(f"  Error {org}: {e}")
            continue

    opportunities.sort(key=lambda x: -x["score"])

    print(f"  Found {len(opportunities)} opportunities. Analyzing top 20...")

    for i, opp in enumerate(opportunities[:20]):
        analysis = analyze_with_ai(opp["title"], opp.get("body", ""), opp["category"])
        opp["ai_analysis"] = analysis
        time.sleep(0.5)

    data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "next_update": (datetime.now() + timedelta(hours=SCAN_INTERVAL_HOURS)).strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(opportunities),
        "opportunities": opportunities
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  Saved {len(opportunities)} opportunities")
    return data


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": None, "next_update": None, "total": 0, "opportunities": []}


def background_scanner():
    scan_opportunities()
    while True:
        time.sleep(SCAN_INTERVAL_HOURS * 3600)
        scan_opportunities()


@app.on_event("startup")
async def startup():
    thread = threading.Thread(target=scan_opportunities, daemon=True)
    thread.start()


@app.get("/api/opportunities")
async def get_opportunities(category: str = None, difficulty: str = None):
    data = load_data()
    opps = data.get("opportunities", [])

    if category and category != "all":
        opps = [o for o in opps if o.get("category") == category]

    if difficulty and difficulty != "all":
        opps = [o for o in opps if o.get("difficulty") == difficulty]

    return {
        "last_updated": data.get("last_updated"),
        "next_update": data.get("next_update"),
        "total": len(opps),
        "opportunities": opps
    }


@app.get("/api/stats")
async def get_stats():
    data = load_data()
    opps = data.get("opportunities", [])

    by_category = {}
    by_difficulty = {}
    by_org = {}

    for opp in opps:
        cat = opp.get("category_label", "Unknown")
        by_category[cat] = by_category.get(cat, 0) + 1

        diff = opp.get("difficulty", "Unknown")
        by_difficulty[diff] = by_difficulty.get(diff, 0) + 1

        org = opp.get("repo", "").split("/")[0]
        by_org[org] = by_org.get(org, 0) + 1

    return {
        "total": len(opps),
        "last_updated": data.get("last_updated"),
        "next_update": data.get("next_update"),
        "by_category": by_category,
        "by_difficulty": by_difficulty,
        "top_orgs": dict(sorted(by_org.items(), key=lambda x: -x[1])[:10])
    }


@app.get("/api/refresh")
async def refresh():
    thread = threading.Thread(target=scan_opportunities, daemon=True)
    thread.start()
    return {"message": "Scan started"}


@app.get("/")
async def root():
    return {"status": "running", "message": "AI Opportunity Dashboard API"}