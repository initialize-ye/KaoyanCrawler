"""数据模型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ListType(str, Enum):
    """名单类型。"""

    RETEST = "复试名单"
    ADMISSION = "录取名单"


@dataclass
class AdmissionRecord:
    """复试/录取记录。"""

    university: str
    year: int
    list_type: ListType
    exam_id: str
    name: str
    major: str
    initial_score: float | None = None
    retest_score: float | None = None
    total_score: float | None = None
    admission_status: str | None = None
    admission_type: str | None = None  # 全日制/非全日制
    study_mode: str | None = None  # 学术型/专业型
    source_url: str = ""
    crawl_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "university": self.university,
            "year": self.year,
            "list_type": self.list_type.value,
            "exam_id": self.exam_id,
            "name": self.name,
            "major": self.major,
            "initial_score": self.initial_score,
            "retest_score": self.retest_score,
            "total_score": self.total_score,
            "admission_status": self.admission_status,
            "admission_type": self.admission_type,
            "study_mode": self.study_mode,
            "source_url": self.source_url,
            "crawl_time": self.crawl_time.isoformat(),
        }


@dataclass
class ExamSubject:
    """考试科目信息。"""

    university: str
    year: int
    major_code: str
    major_name: str
    department: str = ""  # 学院/院系
    research_direction: str = ""  # 研究方向
    enrollment: int | None = None  # 招生人数
    subject1: str | None = None  # 政治
    subject2: str | None = None  # 外语
    subject3: str | None = None  # 业务课一
    subject4: str | None = None  # 业务课二
    retest_score_line: float | None = None  # 复试分数线
    retest_count: int | None = None  # 复试人数
    retest_avg_score: float | None = None  # 复试均分
    admission_count: int | None = None  # 录取人数
    admission_ratio: float | None = None  # 复录比
    admission_min_score: float | None = None  # 录取最低分
    admission_median_score: float | None = None  # 录取中位数
    admission_max_score: float | None = None  # 录取最高分
    admission_avg_score: float | None = None  # 录取平均分
    transfer_type: str = ""  # 调剂类型
    source_url: str = ""
    crawl_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "university": self.university,
            "year": self.year,
            "major_code": self.major_code,
            "major_name": self.major_name,
            "department": self.department,
            "research_direction": self.research_direction,
            "enrollment": self.enrollment,
            "subject1": self.subject1,
            "subject2": self.subject2,
            "subject3": self.subject3,
            "subject4": self.subject4,
            "retest_score_line": self.retest_score_line,
            "retest_count": self.retest_count,
            "retest_avg_score": self.retest_avg_score,
            "admission_count": self.admission_count,
            "admission_ratio": self.admission_ratio,
            "admission_min_score": self.admission_min_score,
            "admission_median_score": self.admission_median_score,
            "admission_max_score": self.admission_max_score,
            "admission_avg_score": self.admission_avg_score,
            "transfer_type": self.transfer_type,
            "source_url": self.source_url,
            "crawl_time": self.crawl_time.isoformat(),
        }


@dataclass
class RetestRule:
    """复试细则/复试办法。"""

    university: str
    year: int
    title: str  # 文件标题，如"XX大学2025年硕士研究生复试录取办法"
    department: str = ""  # 学院（如果是学院级别的细则）
    major: str = ""  # 专业（如果是专业级别的细则）
    content_summary: str = ""  # 内容摘要（AI提取的关键信息）
    retest_format: str = ""  # 复试形式（笔试+面试等）
    score_composition: str = ""  # 成绩构成（初试占比、复试占比等）
    retest_content: str = ""  # 复试内容详情
    other_requirements: str = ""  # 其他要求
    source_url: str = ""
    crawl_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "university": self.university,
            "year": self.year,
            "title": self.title,
            "department": self.department,
            "major": self.major,
            "content_summary": self.content_summary,
            "retest_format": self.retest_format,
            "score_composition": self.score_composition,
            "retest_content": self.retest_content,
            "other_requirements": self.other_requirements,
            "source_url": self.source_url,
            "crawl_time": self.crawl_time.isoformat(),
        }


@dataclass
class ScoreLine:
    """复试分数线。"""

    university: str
    year: int
    category: str  # 学术学位/专业学位
    discipline: str  # 学科门类/专业名称
    total_score: float | None = None
    score1: float | None = None  # 单科1（满分=100分）
    score2: float | None = None  # 单科2（满分>100分）
    discipline_code: str = ""  # 专业代码
    source_url: str = ""
    crawl_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "university": self.university,
            "year": self.year,
            "category": self.category,
            "discipline": self.discipline,
            "discipline_code": self.discipline_code,
            "total_score": self.total_score,
            "score1": self.score1,
            "score2": self.score2,
            "source_url": self.source_url,
            "crawl_time": self.crawl_time.isoformat(),
        }
