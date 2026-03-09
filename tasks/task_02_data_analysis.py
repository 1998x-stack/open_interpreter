#!/usr/bin/env python3
"""
Task 02: Data analysis with CSV statistics and visualization
"""

import csv
import random
import tempfile
import os
from typing import List, Dict, Any
from collections import Counter


def generate_sample_csv(filename: str, num_records: int = 100):
    """Generate a sample CSV file with random data"""
    headers = ['id', 'name', 'age', 'department', 'salary']
    
    departments = ['Engineering', 'Sales', 'Marketing', 'HR', 'Finance']
    names = [
        'Alice Johnson', 'Bob Smith', 'Carol Davis', 'David Wilson', 'Emma Brown',
        'Frank Miller', 'Grace Lee', 'Henry Taylor', 'Ivy Chen', 'Jack Anderson'
    ]
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        
        for i in range(num_records):
            row = [
                i + 1,  # id
                random.choice(names),  # name
                random.randint(22, 65),  # age
                random.choice(departments),  # department
                random.randint(40000, 120000)  # salary
            ]
            writer.writerow(row)


def analyze_csv_data(filename: str) -> Dict[str, Any]:
    """Analyze data from CSV file and return statistics"""
    data = []
    
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Convert numeric fields
            row['id'] = int(row['id'])
            row['age'] = int(row['age'])
            row['salary'] = int(row['salary'])
            data.append(row)
    
    # Calculate statistics
    stats = {}
    
    # Age statistics
    ages = [row['age'] for row in data]
    stats['age_stats'] = {
        'min': min(ages),
        'max': max(ages),
        'avg': sum(ages) / len(ages),
        'median': sorted(ages)[len(ages) // 2]
    }
    
    # Salary statistics
    salaries = [row['salary'] for row in data]
    stats['salary_stats'] = {
        'min': min(salaries),
        'max': max(salaries),
        'avg': sum(salaries) / len(salaries),
        'total': sum(salaries)
    }
    
    # Department breakdown
    departments = [row['department'] for row in data]
    stats['dept_breakdown'] = dict(Counter(departments))
    
    # Top earners
    sorted_by_salary = sorted(data, key=lambda x: x['salary'], reverse=True)
    stats['top_earners'] = sorted_by_salary[:5]
    
    return stats


def visualize_data(stats: Dict[str, Any]):
    """Visualize data using text-based charts"""
    print("Data Visualization (Text-based)")
    print("=" * 40)
    
    # Salary distribution bar chart
    print("\nSalary Distribution (Bar Chart):")
    min_sal = stats['salary_stats']['min']
    max_sal = stats['salary_stats']['max']
    avg_sal = stats['salary_stats']['avg']
    
    print(f"Min: ${min_sal:,} | Max: ${max_sal:,} | Avg: ${avg_sal:,.0f}")
    
    # Department breakdown
    print("\nDepartment Breakdown:")
    dept_counts = stats['dept_breakdown']
    total_people = sum(dept_counts.values())
    
    for dept, count in dept_counts.items():
        percentage = (count / total_people) * 100
        bar_length = int((count / max(dept_counts.values())) * 20)  # Scale to 20 chars max
        bar = '█' * bar_length
        print(f"{dept:12} | {bar:20} | {count:2} ({percentage:.1f}%)")
    
    # Top earners
    print("\nTop 5 Earners:")
    print(f"{'Name':<20} {'Department':<15} {'Salary':<10}")
    print("-" * 47)
    for person in stats['top_earners']:
        print(f"{person['name']:<20} {person['department']:<15} ${person['salary']:<9,}")


def main():
    print("Task 2: Data Analysis with CSV Statistics and Visualization")
    print("=" * 60)
    
    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
        temp_filename = tmp_file.name
    
    try:
        # Generate sample data
        print("Generating sample CSV data...")
        generate_sample_csv(temp_filename, 50)  # Smaller dataset for demo
        
        # Analyze the data
        print("Analyzing CSV data...")
        stats = analyze_csv_data(temp_filename)
        
        # Display statistics
        print("\nAge Statistics:")
        age_stats = stats['age_stats']
        print(f"  Min: {age_stats['min']}, Max: {age_stats['max']}")
        print(f"  Average: {age_stats['avg']:.1f}, Median: {age_stats['median']}")
        
        print("\nSalary Statistics:")
        sal_stats = stats['salary_stats']
        print(f"  Min: ${sal_stats['min']:,}, Max: ${sal_stats['max']:,}")
        print(f"  Average: ${sal_stats['avg']:,.2f}, Total: ${sal_stats['total']:,}")
        
        # Visualize the data
        visualize_data(stats)
        
        print("\nTask completed successfully!")
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)


if __name__ == "__main__":
    main()