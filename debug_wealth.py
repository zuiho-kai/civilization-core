"""调试工具：检测财富变负的位置"""
import sys
import io

# Windows GBK 编码兼容
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith('gbk'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Monkey patch Agent.wealth setter
from civ_kernel.models import Agent

_original_wealth_setter = Agent.wealth.fset if hasattr(Agent.wealth, 'fset') else None

def debug_wealth_setter(self, value):
    if value < 0:
        import traceback
        print(f"\n⚠️  警告：Agent {self.id} 财富变负：{value}")
        print("调用堆栈：")
        traceback.print_stack()
        print()
    # 强制修正为 0
    if _original_wealth_setter:
        _original_wealth_setter(self, max(0, value))
    else:
        self._wealth = max(0, value)

# 如果 wealth 是 property，需要重新定义
if hasattr(Agent, 'wealth') and isinstance(Agent.wealth, property):
    Agent.wealth = property(
        Agent.wealth.fget,
        debug_wealth_setter,
        Agent.wealth.fdel,
        Agent.wealth.__doc__
    )
else:
    # 如果是普通属性，添加 __setattr__ hook
    _original_setattr = Agent.__setattr__

    def debug_setattr(self, name, value):
        if name == 'wealth' and value < 0:
            import traceback
            print(f"\n⚠️  警告：Agent {self.id} 财富变负：{value}")
            print("调用堆栈：")
            traceback.print_stack()
            print()
            value = max(0, value)
        _original_setattr(self, name, value)

    Agent.__setattr__ = debug_setattr

print("✓ 财富调试工具已加载")
