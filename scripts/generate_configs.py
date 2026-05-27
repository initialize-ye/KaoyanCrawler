"""批量生成985院校配置文件。"""

import yaml
from pathlib import Path

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"

# 985院校信息：名称、代码、研究生院URL模式
UNIVERSITIES = [
    {
        "name": "北京大学",
        "code": "pku",
        "grad_url": "https://admission.pku.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生统考拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "清华大学",
        "code": "tsinghua",
        "grad_url": "https://yz.tsinghua.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生统考拟录取名单", "type": "admission_list", "path": "/zsgz/sszs/index.htm"},
        ]
    },
    {
        "name": "中国人民大学",
        "code": "ruc",
        "grad_url": "https://pgs.ruc.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "北京航空航天大学",
        "code": "buaa",
        "grad_url": "https://yzb.buaa.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "北京理工大学",
        "code": "bit",
        "grad_url": "https://grd.bit.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "北京师范大学",
        "code": "bnu",
        "grad_url": "https://yz.bnu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "中央民族大学",
        "code": "muc",
        "grad_url": "https://grs.muc.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "中国农业大学",
        "code": "cau",
        "grad_url": "https://yz.cau.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "天津大学",
        "code": "tju",
        "grad_url": "https://yzb.tju.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "南开大学",
        "code": "nankai",
        "grad_url": "https://yzb.nankai.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "大连理工大学",
        "code": "dlut",
        "grad_url": "https://gs.dlut.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "东北大学",
        "code": "neu",
        "grad_url": "https://yz.neu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "吉林大学",
        "code": "jlu",
        "grad_url": "https://zsb.jlu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "哈尔滨工业大学",
        "code": "hit",
        "grad_url": "https://yzb.hit.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "复旦大学",
        "code": "fudan",
        "grad_url": "https://gsao.fudan.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "上海交通大学",
        "code": "sjtu",
        "grad_url": "https://yzb.sjtu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "同济大学",
        "code": "tongji",
        "grad_url": "https://yz.tongji.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "华东师范大学",
        "code": "ecnu",
        "grad_url": "https://yjszs.ecnu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "南京大学",
        "code": "nju",
        "grad_url": "https://yzb.nju.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "东南大学",
        "code": "seu",
        "grad_url": "https://yzb.seu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "浙江大学",
        "code": "zju",
        "grad_url": "https://grs.zju.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "中国科学技术大学",
        "code": "ustc",
        "grad_url": "https://yz.ustc.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "厦门大学",
        "code": "xmu",
        "grad_url": "https://zs.xmu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "山东大学",
        "code": "sdu",
        "grad_url": "https://www.yz.sdu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "中国海洋大学",
        "code": "ouc",
        "grad_url": "https://yz.ouc.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "武汉大学",
        "code": "whu",
        "grad_url": "https://gs.whu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "华中科技大学",
        "code": "hust",
        "grad_url": "https://gszs.hust.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "中南大学",
        "code": "csu",
        "grad_url": "https://gra.csu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "湖南大学",
        "code": "hnu",
        "grad_url": "https://gra.hnu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "国防科技大学",
        "code": "nudt",
        "grad_url": "https://yjszs.nudt.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "中山大学",
        "code": "sysu",
        "grad_url": "https://graduate.sysu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "华南理工大学",
        "code": "scut",
        "grad_url": "https://admission.scut.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "四川大学",
        "code": "scu",
        "grad_url": "https://yz.scu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "电子科技大学",
        "code": "uestc",
        "grad_url": "https://yz.uestc.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "重庆大学",
        "code": "cqu",
        "grad_url": "https://yz.cqu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "西安交通大学",
        "code": "xjtu",
        "grad_url": "https://yz.xjtu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "西北工业大学",
        "code": "nwpu",
        "grad_url": "https://yzb.nwpu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "兰州大学",
        "code": "lzu",
        "grad_url": "https://yz.lzu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
    {
        "name": "西北农林科技大学",
        "code": "nwafu",
        "grad_url": "https://yjshy.nwafu.edu.cn",
        "targets": [
            {"name": "2025年硕士研究生拟录取名单", "type": "admission_list", "path": "/zsxx/sszs/index.htm"},
        ]
    },
]


def generate_config(uni: dict) -> dict:
    """生成单个学校的配置。"""
    targets = []
    for t in uni["targets"]:
        target = {
            "name": t["name"],
            "type": t["type"],
            "url": uni["grad_url"] + t["path"],
            "format": "html",
            "selectors": {
                "table": "table",
                "row": "tr",
                "columns": {
                    0: "exam_id",
                    1: "name",
                    2: "major",
                    3: "initial_score",
                    4: "retest_score",
                    5: "total_score",
                    6: "admission_status",
                }
            },
            "parse_rules": {
                "year": 2025,
                "list_type": "录取名单",
            }
        }
        targets.append(target)

    return {
        "name": uni["name"],
        "code": uni["code"],
        "graduate_school_url": uni["grad_url"],
        "tags": ["985", "211"],
        "targets": targets,
    }


def main():
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)

    for uni in UNIVERSITIES:
        config = generate_config(uni)
        config_file = CONFIGS_DIR / f"{uni['code']}.yaml"

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        print(f"  生成: {config_file.name}")

    print(f"\n共生成 {len(UNIVERSITIES)} 个配置文件")


if __name__ == "__main__":
    main()
