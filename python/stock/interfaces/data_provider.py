from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List, Protocol, Iterable, Dict, Any
import pandas as pd

@dataclass
class BarRequest:
    symbols: List[str]
    start: date
    end: date
    fields: List[str] | None = None  # None => default set

class DataProvider(ABC):
    @abstractmethod
    def get_index_members(self, index_code: str, as_of: date) -> List[str]:
        """Return component symbols (e.g. '000300.SH') at a date (use latest before as_of)."""

    @abstractmethod
    def get_daily_bars(self, req: BarRequest) -> pd.DataFrame:
        """Return DataFrame columns: ['date','symbol','open','high','low','close','preclose','volume','amount','adj_factor']"""

    @abstractmethod
    def get_basic_info(self) -> pd.DataFrame:
        """Return symbol static info: ['symbol','name','list_date','is_st','market','exchange']"""

    @abstractmethod
    def get_corporate_actions(self, symbols: Iterable[str]) -> pd.DataFrame:
        """Return corporate actions for adjustment if needed."""

class Strategy(Protocol):
    def generate_target_weights(self, trade_date: date, universe: List[str], data_ctx: Dict[str, Any]) -> Dict[str, float]:
        ...
