def calculate_profit_distribution(net_profit, employees, mode, params):
    if net_profit <= 0:
        return {'error': 'No profit to distribute'}

    if mode == 'fixed_percentage':
        # params: {'owners': [{'id':1, 'pct':40}, ...], 'reinvestment':40}
        owners = params.get('owners', [])
        reinvestment = params.get('reinvestment', 0)
        distribution = {}
        for owner in owners:
            distribution[owner['id']] = net_profit * owner['pct'] / 100
        distribution['reinvestment'] = net_profit * reinvestment / 100
        return distribution

    elif mode == 'per_head_equal':
        n = len(employees)
        payout = net_profit / n if n > 0 else 0
        return {emp.id: payout for emp in employees}

    elif mode == 'pro_rata_salary':
        total_salary = sum(emp.base_salary for emp in employees)
        if total_salary == 0:
            return {emp.id: 0 for emp in employees}
        return {emp.id: net_profit * (emp.base_salary / total_salary) for emp in employees}

    elif mode == 'hybrid':
        # params: fixed salaries, bonus share
        fixed_total = sum(emp.base_salary for emp in employees)
        if net_profit <= fixed_total:
            return {emp.id: emp.base_salary for emp in employees}
        bonus_pool = net_profit - fixed_total
        # Assume equal bonus or pro-rata, but for simplicity, pro-rata by salary
        total_salary = sum(emp.base_salary for emp in employees)
        distribution = {}
        for emp in employees:
            fixed = emp.base_salary
            bonus = bonus_pool * (emp.base_salary / total_salary) if total_salary > 0 else 0
            distribution[emp.id] = fixed + bonus
        return distribution

    elif mode == 'custom':
        # params: {'allocations': {emp_id: pct or amount}}
        allocations = params.get('allocations', {})
        distribution = {}
        for emp in employees:
            alloc = allocations.get(str(emp.id), 0)
            if isinstance(alloc, float) and alloc <= 1:  # percentage
                distribution[emp.id] = net_profit * alloc
            else:  # fixed amount
                distribution[emp.id] = alloc
        return distribution

    else:
        return {'error': 'Unknown mode'}
