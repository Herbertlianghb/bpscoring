# 自动评分系统

这是一个基于Python的自动评分系统，用于评估Word文档中的答案。

## 功能特点

- 支持Word文档格式的答案文件
- 使用jieba进行中文分词
- 使用BM25算法进行相似度匹配
- 自动生成Excel格式的评分报告
- 支持批量处理多个答案文件

## 安装说明

1. 确保已安装Python 3.8或更高版本
2. 安装依赖包：
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

1. 配置环境变量：
   - 创建 `.env` 文件
   - 添加以下配置：
     ```
     DEEPSEEK_API_KEY=your_api_key_here
     ```

2. 准备标准答案：
   - 编辑 `standard_answers.json` 文件
   - 按照格式添加标准答案

3. 准备答案文件：
   - 在 `submissions` 目录中放入需要评分的Word文档
   - 每个文档中的段落按顺序对应问题

4. 运行评分程序：
   ```bash
   python auto_score.py
   ```

5. 查看结果：
   - 评分结果将保存在 `scoring_results.xlsx` 文件中
   - 包含每个答案的得分和总分

## 注意事项

- 请确保Word文档格式正确
- 答案段落顺序要与标准答案对应
- 不要将API密钥提交到版本控制系统
- 定期备份评分结果

## 文件说明

- `auto_score.py`: 主程序文件
- `standard_answers.json`: 标准答案文件
- `requirements.txt`: 项目依赖文件
- `.env`: 环境变量配置文件
- `submissions/`: 存放待评分答案的目录
- `scoring_results.xlsx`: 评分结果文件

## 安全提示

- 请妥善保管API密钥
- 不要将包含敏感信息的文件提交到版本控制系统
- 定期更新依赖包以修复安全漏洞 