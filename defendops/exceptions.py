"""DefendOps 异常类型。"""


class ConfigError(Exception):
    """配置缺失或非法。通常是没配模型 / API key。"""


class ModelUnavailableError(Exception):
    """模型不可用（探活失败、调用失败且无备用）。不降级、不兜底，直接抛。"""
