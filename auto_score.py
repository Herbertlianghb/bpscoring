import os, re, json, asyncio, uuid
from pathlib import Path
from docx import Document
import jieba, pandas as pd, tiktoken
from rank_bm25 import BM25Okapi
import aiohttp
from tqdm.asyncio import tqdm_asyncio

API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL   = "deepseek-chat"
TEMPERATURE = 0
CONCURRENCY = 6
K_EVID = 5
MAX_EVID_TOK = 350
DOCX_FILE = "bizplan.docx"
SCORECARD_FILE = "scorecard.json"

# 直接在代码中设置API密钥，不再需要环境变量
API_KEY = "sk-b19e3d70b01f40a181ab57ccc92cbeb0"

def docx_to_sentences(path):
    doc = Document(path)
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paras)
    return [s.strip() for s in re.split(r"(?<=[。！？；\n])", text) if s.strip()]

sentences = docx_to_sentences(DOCX_FILE)
tok_sents = [list(jieba.cut(s)) for s in sentences]
bm25 = BM25Okapi(tok_sents)
enc = tiktoken.get_encoding("cl100k_base")

scorecard = json.loads(Path(SCORECARD_FILE).read_text(encoding="utf-8"))
criteria = {sc["id"]: sc for dim in scorecard for sc in dim["subcriteria"]}

def get_evidence(query, k=K_EVID):
    q_tok = list(jieba.cut(query))
    idx = sorted(range(len(sentences)),
                 key=lambda i: -bm25.get_scores(q_tok)[i])[:k]
    evid, tok = [], 0
    for i in idx:
        st = sentences[i]
        tok += len(enc.encode(st))
        if tok > MAX_EVID_TOK: break
        evid.append(f"[{i}] {st}")
    return "\n".join(evid)

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

async def chat(messages):
    async with aiohttp.ClientSession() as sess:
        try:
            async with sess.post(API_URL, headers=HEADERS,
                                json={"model": MODEL, "temperature": TEMPERATURE,
                                      "messages": messages}, timeout=120) as resp:
                response = await resp.json()
                print(f"API响应: {response}")  # 打印API响应
                if resp.status != 200:
                    print(f"API错误: {response}")
                    return '{"score": 1, "reason": "API调用失败"}'
                try:
                    return response["choices"][0]["message"]["content"]
                except (KeyError, IndexError) as e:
                    print(f"API响应格式错误: {response}")
                    return '{"score": 1, "reason": "API响应格式错误"}'
        except Exception as e:
            print(f"API请求异常: {str(e)}")
            return '{"score": 1, "reason": "API请求异常"}'

async def score_one(cid):
    try:
        crit = criteria[cid]
        evidence = get_evidence(crit["text"])
        sys = {"role": "system", "content": (
            "你是一位中国高校创新创业大赛评委。\n"
            "评分项说明：" + crit["text"] + "\n"
            "评分锚点：" + json.dumps(crit["scoring_anchors"], ensure_ascii=False))}
        usr = {"role": "user", "content": (
            f"以下是与该评分项最相关的内容证据：\n{evidence}\n\n"
            "请基于锚点给出 1-5 分并返回 JSON格式：\n"
            '{"score": 数字(1-5), "reason": "评分理由"}')}
        print(f"\n评分项 {cid}:")  # 打印当前评分项
        print(f"系统提示: {sys['content']}")  # 打印系统提示
        print(f"用户输入: {usr['content']}")  # 打印用户输入
        res = await chat([sys, usr])
        print(f"API返回: {res}")  # 打印API返回
        try:
            # 尝试直接解析JSON
            return cid, json.loads(res)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {str(e)}")
            # 尝试提取JSON部分
            import re
            json_pattern = r'\{\s*"score"\s*:\s*([1-5])\s*,\s*"reason"\s*:\s*"(.+?)"\s*\}'
            match = re.search(json_pattern, res)
            if match:
                score = int(match.group(1))
                reason = match.group(2)
                return cid, {"score": score, "reason": reason}
            # 如果无法提取，返回默认值
            return cid, {"score": 1, "reason": f"无法解析API返回: {res[:100]}..."}
    except Exception as e:
        print(f"评分出错 {cid}: {str(e)}")
        return cid, {"score": 1, "reason": f"评分过程出错: {str(e)}"}

async def main():
    print("开始评分...")
    sem = asyncio.Semaphore(CONCURRENCY)
    async def sem_task(cid):
        async with sem:
            return await score_one(cid)
    tasks = [sem_task(c) for c in criteria]
    results = await tqdm_asyncio.gather(*tasks)
    scores = {cid: obj for cid, obj in results}

    weight = {"E":30,"I":30,"T":15,"C":15,"S":15}
    # 初始化维度得分和计数
    subtotal = {k:0 for k in weight}
    dim_count = {k:0 for k in weight}
    
    # 累计各维度得分和计数
    for cid, obj in scores.items():
        dim = cid[0]
        subtotal[dim] += obj["score"]
        dim_count[dim] += 1
    
    # 计算维度平均分并乘以权重
    for dim in weight:
        if dim_count[dim] > 0:
            subtotal[dim] = (subtotal[dim] / dim_count[dim]) * weight[dim] / 5
    
    total = round(sum(subtotal.values()), 2)

    tag = uuid.uuid4().hex[:6]
    json_path, csv_path = f"score_{tag}.json", f"score_{tag}.csv"
    Path(json_path).write_text(json.dumps(
        {"total": total, "dim_scores": subtotal, "detail": scores},
        ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame([{"维度":k,"得分":v} for k,v in subtotal.items()]) \
        .to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n✔ 评分完成，总分 {total}")
    print("结果文件：", json_path, "/", csv_path)

if __name__ == "__main__":
    asyncio.run(main())