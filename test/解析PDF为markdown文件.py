import pymupdf4llm

# 指定你的 PDF 文件路径
pdf_path = "测试.pdf"

# 将 PDF 转换为 Markdown 文本
md_text = pymupdf4llm.to_markdown(pdf_path)

# 可选：保存为 .md 文件
output_path = "output.md"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(md_text)

print("✅ 转换完成！Markdown 内容预览（前500字符）：")
print(md_text[:500] + "...")