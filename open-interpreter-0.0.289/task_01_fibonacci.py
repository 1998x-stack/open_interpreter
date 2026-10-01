"""
任务编号: task_01_fibonacci.py
功能描述: 斐波那契数列计算 + 性能分析
包含多种实现方式及其性能对比分析
"""

import time
import functools
from typing import Generator
import matplotlib.pyplot as plt

class FibonacciCalculator:
    """
    斐波那契数列计算器，包含多种实现方法及性能分析
    """
    
    def __init__(self):
        self.memo = {}
    
    def recursive_basic(self, n: int) -> int:
        """
        基础递归实现（效率低）
        时间复杂度: O(2^n)
        空间复杂度: O(n)
        """
        if n <= 1:
            return n
        return self.recursive_basic(n - 1) + self.recursive_basic(n - 2)
    
    def recursive_memo(self, n: int) -> int:
        """
        记忆化递归实现
        时间复杂度: O(n)
        空间复杂度: O(n)
        """
        if n in self.memo:
            return self.memo[n]
        
        if n <= 1:
            result = n
        else:
            result = self.recursive_memo(n - 1) + self.recursive_memo(n - 2)
        
        self.memo[n] = result
        return result
    
    @functools.lru_cache(maxsize=None)
    def recursive_lru_cache(self, n: int) -> int:
        """
        使用LRU缓存的递归实现
        时间复杂度: O(n)
        空间复杂度: O(n)
        """
        if n <= 1:
            return n
        return self.recursive_lru_cache(n - 1) + self.recursive_lru_cache(n - 2)
    
    def iterative_bottom_up(self, n: int) -> int:
        """
        自底向上迭代实现
        时间复杂度: O(n)
        空间复杂度: O(1)
        """
        if n <= 1:
            return n
        
        prev, curr = 0, 1
        for _ in range(2, n + 1):
            prev, curr = curr, prev + curr
        return curr
    
    def matrix_power(self, n: int) -> int:
        """
        矩阵快速幂实现
        时间复杂度: O(log n)
        空间复杂度: O(log n)
        """
        if n <= 1:
            return n
        
        def matrix_multiply(A, B):
            """矩阵乘法"""
            return [[A[0][0]*B[0][0] + A[0][1]*B[1][0], A[0][0]*B[0][1] + A[0][1]*B[1][1]],
                    [A[1][0]*B[0][0] + A[1][1]*B[1][0], A[1][0]*B[0][1] + A[1][1]*B[1][1]]]
        
        def matrix_power(matrix, power):
            """矩阵快速幂"""
            if power == 1:
                return matrix
            if power % 2 == 0:
                half_power = matrix_power(matrix, power // 2)
                return matrix_multiply(half_power, half_power)
            else:
                return matrix_multiply(matrix, matrix_power(matrix, power - 1))
        
        base_matrix = [[1, 1], [1, 0]]
        result_matrix = matrix_power(base_matrix, n)
        return result_matrix[0][1]
    
    def generator_sequence(self, max_n: int) -> Generator[int, None, None]:
        """
        生成器实现，逐个生成斐波那契数列
        """
        a, b = 0, 1
        count = 0
        while count <= max_n:
            yield a
            a, b = b, a + b
            count += 1


def measure_performance(func, n: int, *args, **kwargs) -> tuple:
    """
    测量函数执行时间和内存使用情况
    返回: (执行时间, 结果, 函数名)
    """
    start_time = time.time()
    result = func(n, *args, **kwargs)
    end_time = time.time()
    
    execution_time = end_time - start_time
    return execution_time, result, func.__name__


def run_performance_analysis():
    """
    运行性能分析
    """
    calc = FibonacciCalculator()
    
    # 只测试较小的n值以避免基本递归耗时过长
    test_values = [10, 20, 30]
    
    methods = [
        (calc.iterative_bottom_up, "自底向上迭代"),
        (calc.recursive_memo, "记忆化递归"),
        (calc.recursive_lru_cache, "LRU缓存递归"),
        (calc.matrix_power, "矩阵快速幂")
    ]
    
    # 对于基础递归，只在小数值上测试
    basic_recursive_test = [(calc.recursive_basic, "基础递归")]
    
    print("=" * 60)
    print("斐波那契数列计算 - 性能分析报告")
    print("=" * 60)
    
    for n in test_values:
        print(f"\n计算第 {n} 个斐波那契数:")
        print("-" * 40)
        
        # 首先测试基础递归（仅对小数值）
        if n <= 35:  # 限制基础递归的测试范围，避免过长时间等待
            exec_time, result, name = measure_performance(calc.recursive_basic, n)
            print(f"{name:15} : {result:>15} (耗时: {exec_time:.6f}s)")
        
        # 测试其他方法
        for method, name in methods:
            # 清空memo以确保每次测试公正
            if hasattr(method, '__name__') and 'memo' in method.__name__:
                calc.memo.clear()
            
            exec_time, result, func_name = measure_performance(method, n)
            print(f"{name:15} : {result:>15} (耗时: {exec_time:.6f}s)")
    
    # 生成数列示例
    print(f"\n前 10 个斐波那契数:")
    print("-" * 40)
    fib_gen = calc.generator_sequence(9)
    sequence = list(fib_gen)
    print(f"数列: {sequence}")
    
    # 性能对比总结
    print(f"\n算法复杂度对比:")
    print("-" * 40)
    complexities = [
        ("基础递归", "O(2^n)", "O(n)"),
        ("记忆化递归", "O(n)", "O(n)"),
        ("LRU缓存递归", "O(n)", "O(n)"),
        ("自底向上迭代", "O(n)", "O(1)"),
        ("矩阵快速幂", "O(log n)", "O(log n)")
    ]
    
    print(f"{'算法':15} {'时间复杂度':10} {'空间复杂度':10}")
    for alg, time_c, space_c in complexities:
        print(f"{alg:15} {time_c:10} {space_c:10}")
    
    print("\n结论:")
    print("- 对于大数值计算，推荐使用矩阵快速幂算法")
    print("- 对于一般用途，自底向上迭代算法效率高且节省空间")
    print("- 对于需要多次调用的场景，记忆化递归是不错的选择")


def advanced_analysis():
    """
    高级分析：绘制性能曲线
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        calc = FibonacciCalculator()
        methods = [
            (calc.iterative_bottom_up, "自底向上迭代"),
            (calc.recursive_memo, "记忆化递归"), 
            (calc.matrix_power, "矩阵快速幂")
        ]
        
        # 测试不同规模的输入
        test_ns = list(range(10, 31, 5))  # 10, 15, 20, 25, 30
        results = {name: [] for _, name in methods}
        
        print(f"\n高级性能分析中...")
        for n in test_ns:
            for method, name in methods:
                # 清空memo
                if hasattr(calc, 'memo'):
                    calc.memo.clear()
                
                exec_time, _, _ = measure_performance(method, n)
                results[name].append(exec_time)
        
        # 绘制性能对比图
        plt.figure(figsize=(12, 8))
        for name in results:
            plt.plot(test_ns, results[name], marker='o', label=name, linewidth=2)
        
        plt.title('斐波那契算法性能对比', fontsize=16)
        plt.xlabel('输入值 n', fontsize=12)
        plt.ylabel('执行时间 (秒)', fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.yscale('log')  # 使用对数刻度以便更好地显示差异
        
        print("性能对比图表已准备就绪（如需显示，请在支持图形界面的环境中运行）")
        
    except ImportError:
        print("\n注意: matplotlib未安装，无法生成性能图表")
        print("可使用 'pip install matplotlib' 安装以查看可视化结果")


if __name__ == "__main__":
    print("任务: task_01_fibonacci.py")
    print("功能: 斐波那契数列计算 + 性能分析")
    print()
    
    # 运行性能分析
    run_performance_analysis()
    
    # 运行高级分析
    advanced_analysis()
    
    print("\n" + "="*60)
    print("任务完成！已提供多种斐波那契实现方式的性能对比分析。")
    print("="*60)