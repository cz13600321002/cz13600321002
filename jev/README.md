# 用 Jev 给文档入库

Jev 是 TypeSafe 的 System One 模型。一次请求提交文档状态和一组定型问题，返回选项、分数和概率，由这段程序决定放哪、要不要自动移动。

适合它做的事：目录是封闭集合，正文是不是空白模板，有没有时间压力。日期、文件名和「置信度不够就留给人」都在代码里。

## 准备

```bash
cd jev
python3 -m pip install -e .
export TYPESAFE_API_KEY='你的密钥'
```

密钥在 [console.typesafe.ai/settings/keys](https://console.typesafe.ai/settings/keys)。

## 使用

在文库根目录：

```bash
python3 -m jev_file jev/fixtures/会议纪要_已填写.md jev/fixtures/空白周报.md
python3 -m jev_file --apply 某份成稿.md
python3 -m jev_file --json 某份成稿.md
```

默认只打印建议。`--apply` 只移动判定为「可入库」的文件，不覆盖已有文件。

当前模型对中文不如英文稳，所以自动入库要求目录置信度至少 0.80，并且模型明确认为这不是空白模板。这组门槛还没用本库的真实文档校准过，应先看几份结果再调整 `jev/src/jev_file/questions.py` 里的常数。

每次调用使用的模型别名是 `jev-latest`。输出里的「模型」是实际回答的版本号。
