#!/usr/bin/env python3
"""
Task 01: Fibonacci sequence with performance analysis
"""

import time
from typing import List


def fibonacci_recursive(n: int) -> int:
    """Calculate nth Fibonacci number recursively (inefficient for large n)"""
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


def fibonacci_iterative(n: int) -> int:
    """Calculate nth Fibonacci number iteratively (efficient)"""
    if n <= 1:
        return n
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def fibonacci_sequence(n: int) -> List[int]:
    """Generate Fibonacci sequence up to nth term"""
    if n < 0:
        return []
    if n == 0:
        return [0]
    
    sequence = [0, 1]
    for i in range(2, n + 1):
        sequence.append(sequence[i-1] + sequence[i-2])
    
    return sequence


def performance_test():
    """Compare performance of different Fibonacci implementations"""
    test_values = [5, 10, 15, 20, 30]
    
    print("Fibonacci Performance Comparison:")
    print("n\tRecursive\tIterative")
    print("-" * 35)
    
    for n in test_values:
        # Test iterative (always run this)
        start_time = time.time()
        result_iter = fibonacci_iterative(n)
        iter_time = time.time() - start_time
        
        # Test recursive (skip for large n as it takes too long)
        if n <= 30:  # Recursive gets slow after this
            start_time = time.time()
            result_rec = fibonacci_recursive(n)
            rec_time = time.time() - start_time
            print(f"{n}\t{rec_time:.6f}s\t{iter_time:.6f}s")
        else:
            print(f"{n}\t>10s\t\t{iter_time:.6f}s")


def main():
    print("Task 1: Fibonacci Sequence Analysis")
    print("=" * 40)
    
    # Generate and display Fibonacci sequence
    n = 10
    sequence = fibonacci_sequence(n)
    print(f"Fibonacci sequence up to {n}: {sequence}")
    
    # Calculate a specific Fibonacci number
    n_specific = 15
    fib_num = fibonacci_iterative(n_specific)
    print(f"\nThe {n_specific}th Fibonacci number is: {fib_num}")
    
    # Performance comparison
    print("\nPerformance Analysis:")
    performance_test()
    
    print("\nTask completed successfully!")


if __name__ == "__main__":
    main()