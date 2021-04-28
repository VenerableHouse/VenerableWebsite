#!/usr/bin/env python3

from enum import Enum
from typing import Type

from sqlalchemy import func, Integer, TypeDecorator

class IntEnum(TypeDecorator):
    impl = Integer
    enum_type: Type[Enum]

    def __init__(self, enum_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_type = enum_type

    def process_bind_param(self, enum: Enum, dialect) -> int:
        if isinstance(enum, self.enum_type):
            return enum.value
        raise ValueError(
            f"Expected argument of type {self.enum_type}, received {enum.__class__}"
        )

    def process_result_value(self, value: int, dialect) -> Enum:
        return self.enum_type(value)

# handy-dandy helper function: sum, but empty sums are 0
def nonnull_sum(col):
  return func.coalesce(func.sum(col), 0)
