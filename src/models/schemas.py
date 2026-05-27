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
    subject1: str | None = None  # 政治
    subject2: str | None = None  # 外语
    subject3: str | None = None  # 业务课一
    subject4: str | None = None  # 业务课二
    source_url: str = ""
    crawl_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "university": self.university,
            "year": self.year,
            "major_code": self.major_code,
            "major_name": self.major_name,
            "subject1": self.subject1,
            "subject2": self.subject2,
            "subject3": self.subject3,
            "subject4": self.subject4,
            "source_url": self.source_url,
            "crawl_time": self.crawl_time.isoformat(),
        }
