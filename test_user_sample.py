import sys
sys.stdout.reconfigure(encoding="utf-8")
from app.chinese_recap_processor import preprocess_chinese_drama_text
from app.transcriber import naturalize_burmese_recap

test_lines = [
    "大师兄竟然是鲛人。",
    "为了救我，",
    "误中了魔修的剧毒。",
    "结果连头发都被逼成了带毒的颜色。",
    "鲛人不可言说的躁动……",
    "“小孩不听话，”",
    "“是想让师兄惩罚你吗？”",
    "完了。",
    "大师兄……",
    "我叫风戚宁。",
    "叶晚舟是我最讨厌的人。",
    "在他来宗门之前，",
    "我是全宗门最瞩目的大师姐。",
    "可自从他来了以后，一切都变了。",
    "他的修炼天赋在我之上，",
    "雷法实力也远比我强横，",
    "连容貌与人缘都远胜于我。",
    "彻底把我甩在身后。",
    "每次见到师弟师妹和执法长老，我都一阵心虚。",
    "全宗上下都念着他的名字。",
    "他众望所归被推选为——",
    "大家最想求教的首席大师兄。",
    "从此以后，我成了二师姐。",
    "我憋着一口气，狠狠咽了下去。",
    "走着瞧！",
    "那一夜我暗暗发誓：",
    "一定要亲手打败你！",
    "“二师姐，好啊。”",
    "若不加紧修炼，",
    "我随时都会彻底输给你。",
    "你给我看着，",
    "你等着！",
    "十年之内，",
    "我一定会赢你！",
    "可那时我怎么也没想到，",
    "我再也没有机会赢过叶晚舟了……"
]

print("=== TRANSLATION RESULTS ===")
for idx, line in enumerate(test_lines, 1):
    res = naturalize_burmese_recap(preprocess_chinese_drama_text(line))
    print(f"{idx}. {res}")
