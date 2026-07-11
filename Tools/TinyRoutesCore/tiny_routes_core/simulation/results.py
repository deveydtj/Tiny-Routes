from enum import Enum

class LevelOutcome(str, Enum):
    IN_PROGRESS = "inProgress"
    COMPLETED = "completed"
    FAILED_DEAD_END = "failedDeadEnd"
    FAILED_MISSING_PACKAGE = "failedMissingPackage"
    FAILED_TIME_LIMIT = "failedTimeLimit"
