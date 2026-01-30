import langgraph
import Load_Info
import Sheets
from typing_extensions import TypedDict

class State(TypedDict):
    canvas_assignments: list[dict]
    sheet_assignments: list[dict]
    logs: list[str]
    ops: list[dict]
    



