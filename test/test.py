# import re
#
# text = '''# 斗破苍穹
#
# 第一章 陨落的天才()
#
# “斗之力，三段！”
#
# 望着测验魔石碑上面闪亮得甚至有些刺眼的五个大字，少年面无表情，唇角有着一抹自
# 嘲，紧握的手掌，因为大力，而导致略微尖锐的指甲深深的刺进了掌心之中，带来一阵阵钻
# 心的疼痛…
#
# “萧炎，斗之力，三段！级别：低级！”测验魔石碑之旁，一位中年男子，看了一眼碑
# 上所显示出来的信息，语气漠然的将之公布了出来…
#
# 中年男子话刚刚脱口，便是不出意外的在人头汹涌的广场上带起了一阵嘲讽的骚动.
#
# ![](D:/llm/大模型实战项目/llamaindex实战案例-新/file/image/斗破苍穹.pdf-0-0.png)
#
# “三段？嘿嘿，果然不出我所料，这个"天才"这一年又是在原地踏步！”
#
# “哎，这废物真是把家族的脸都给丢光了。”'''
#
# # 使用方案二：匹配完整的Markdown图片语法
# pattern = r'!\[.*?\]\((D:/llm/[^)]+\.png)\)'
# matches = re.findall(pattern, text)
#
# print("匹配到的路径:")
# for match in matches:
#     print(match)
#
# # 如果只想匹配路径部分
# path_pattern = r'D:/llm/[^)]+\.png'
# path_matches = re.findall(path_pattern, text)
# print("\n直接匹配的路径:")
# for path in path_matches:
#     print(path)

from llama_index.core.postprocessor import SentenceTransformerRerank

reranker = SentenceTransformerRerank(model=r"D:\llm\Local_model\BAAI\bge-reranker-large")