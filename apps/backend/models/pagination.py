from pydantic import BaseModel
import math


class Pagination(BaseModel):
    size: int = 0
    totalElements: int = 0
    totalPages: int = 0
    scrollId: str = ''

    @staticmethod
    def count_total_pages(size, count):
        return Pagination(size=size,
                          totalElements=count,
                          totalPages=math.ceil(count / size) if count else 0)
