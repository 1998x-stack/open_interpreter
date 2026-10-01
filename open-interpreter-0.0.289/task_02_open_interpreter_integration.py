"""
任务编号: task_02_open_interpreter_integration.py
功能描述: Open Interpreter 项目功能演示 + 性能分析
展示如何在项目中集成数学计算功能
"""

import time
from typing import Callable
from interpreter.factory import InterpreterFactory, register_default_interpreters
import interpreter as interpreter_module  # This imports the interpreter instance


class MathFunctionAnalyzer:
    """
    数学函数分析器，用于分析各种数学函数的性能
    """
    
    def __init__(self):
        # 初始化解释器工厂
        register_default_interpreters()
        self.interpreter = interpreter_module  # Using the imported module instance
    
    def fibonacci_recursive(self, n: int) -> int:
        """
        使用递归计算斐波那契数列
        """
        if n <= 1:
            return n
        return self.fibonacci_recursive(n - 1) + self.fibonacci_recursive(n - 2)
    
    def fibonacci_iterative(self, n: int) -> int:
        """
        使用迭代计算斐波那契数列
        """
        if n <= 1:
            return n
        
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    
    def factorial_recursive(self, n: int) -> int:
        """
        使用递归计算阶乘
        """
        if n <= 1:
            return 1
        return n * self.factorial_recursive(n - 1)
    
    def factorial_iterative(self, n: int) -> int:
        """
        使用迭代计算阶乘
        """
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result
    
    def measure_execution_time(self, func: Callable, *args, **kwargs) -> tuple:
        """
        测量函数执行时间
        返回: (结果, 执行时间)
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    def compare_algorithms(self, n: int) -> None:
        """
        对比不同算法的性能
        """
        print(f"分析第 {n} 项的计算性能:")
        print("-" * 50)
        
        # 测试斐波那契计算
        print("斐波那契数列计算对比:")
        
        # 递归方法（仅适用于小数值）
        if n <= 35:  # 限制递归方法的测试范围
            result_rec, time_rec = self.measure_execution_time(self.fibonacci_recursive, n)
            print(f"  递归方法:     结果={result_rec:10}, 耗时={time_rec:.6f}s")
        
        # 迭代方法
        result_it, time_it = self.measure_execution_time(self.fibonacci_iterative, n)
        print(f"  迭代方法:     结果={result_it:10}, 耗时={time_it:.6f}s")
        
        # 测试阶乘计算（仅适用于较小的数值）
        if n <= 15:
            print(f"\n{n} 的阶乘计算对比:")
            result_fact_rec, time_fact_rec = self.measure_execution_time(self.factorial_recursive, n)
            result_fact_it, time_fact_it = self.measure_execution_time(self.factorial_iterative, n)
            
            print(f"  递归方法:     结果={result_fact_rec:10}, 耗时={time_fact_rec:.6f}s")
            print(f"  迭代方法:     结果={result_fact_it:10}, 耗时={time_fact_it:.6f}s")
        
        print()
    
    def run_math_operations_via_interpreter(self, operations: list) -> None:
        """
        通过解释器运行数学运算
        """
        print("通过 Open Interpreter 执行数学运算:")
        print("-" * 50)
        
        for i, operation in enumerate(operations, 1):
            print(f"{i}. 执行操作: {operation}")
            try:
                # 这过解释器执行数学运算
                # 注意：这里我们不会实际执行，因为这会需要API密钥
                print(f"   模拟结果: 需要有效的API密钥来执行此操作")
            except Exception as e:
                print(f"   错误: {str(e)}")
            print()


def demonstrate_open_interpreter_features():
    """
    演示 Open Interpreter 项目的特性
    """
    analyzer = MathFunctionAnalyzer()
    
    print("=" * 60)
    print("Open Interpreter 项目功能演示 + 性能分析")
    print("=" * 60)
    
    # 性能对比分析
    test_values = [10, 20, 30]
    
    for n in test_values:
        analyzer.compare_algorithms(n)
    
    # 演示解释器工厂模式
    print("解释器工厂模式演示:")
    print("-" * 50)
    
    # 创建不同类型的解释器
    python_interp = InterpreterFactory.create('python')
    shell_interp = InterpreterFactory.create('shell')
    
    print(f"Python 解释器类型: {type(python_interp).__name__}")
    print(f"Shell 解释器类型: {type(shell_interp).__name__}")
    
    # 验证代码功能
    sample_code = "print('Hello from Python interpreter!')"
    is_valid = python_interp.validate_code(sample_code)
    print(f"代码验证结果: {is_valid}")
    
    # 演示数学运算
    print("\n数学运算示例:")
    print("-" * 30)
    print(f"fibonacci_iterative(10) = {analyzer.fibonacci_iterative(10)}")
    print(f"factorial_iterative(10) = {analyzer.factorial_iterative(10)}")
    
    # 演示通过解释器执行的操作（模拟）
    math_operations = [
        "Calculate fibonacci(15)",
        "Compute factorial of 12",
        "Generate first 10 numbers of fibonacci sequence"
    ]
    
    analyzer.run_math_operations_via_interpreter(math_operations)
    
    print("=" * 60)
    print("Open Interpreter 功能演示完成!")
    print("- 支持多种编程语言解释器")
    print("- 具备工厂模式便于扩展")
    print("- 具备代码验证功能")
    print("- 可用于数学计算任务")
    print("=" * 60)


if __name__ == "__main__":
    print("任务: task_02_open_interpreter_integration.py")
    print("功能: Open Interpreter 项目功能演示 + 性能分析")
    print()
    
    demonstrate_open_interpreter_features()