from app.models import Business, BusinessType

class BusinessTypeService:
    @staticmethod
    def get_business_features(business_id):
        """Get enabled features for a business based on its type"""
        business = Business.query.get(business_id)
        if not business or not business.business_type_obj:
            # Default features if no business type set
            return {
                'inventory': True,
                'customers': True,
                'sales_goals': True,
                'reports': True,
                'analytics': True,
                'notifications': True,
            }

        bt = business.business_type_obj
        return {
            'inventory': bt.enable_inventory,
            'recipes': bt.enable_recipes,
            'customers': bt.enable_customers,
            'projects': bt.enable_projects,
            'campaigns': bt.enable_campaigns,
            'payroll': bt.enable_payroll,
            'budgets': bt.enable_budgets,
            'suppliers': bt.enable_suppliers,
            'sales_goals': bt.enable_sales_goals,
            'time_tracking': bt.enable_time_tracking,
            'invoices': bt.enable_invoices,
            'contracts': bt.enable_contracts,
            'marketing': bt.enable_marketing,
            'reports': bt.enable_reports,
            'analytics': bt.enable_analytics,
            'notifications': bt.enable_notifications,
        }

    @staticmethod
    def get_navigation_menu(business_id):
        """Get navigation menu items based on business type"""
        features = BusinessTypeService.get_business_features(business_id)

        menu_items = []

        # Business submenu
        business_menu = []
        business_menu.append({'name': 'Manage Roles', 'url': 'web.manage_roles', 'icon': 'fas fa-users-cog'})
        business_menu.append({'name': 'All Features', 'url': 'web.features_overview', 'icon': 'fas fa-star'})

        if features.get('analytics'):
            business_menu.append({'name': 'Analytics', 'url': 'web.business_analytics_dashboard', 'icon': 'fas fa-chart-line'})

        if features.get('inventory'):
            business_menu.append({'name': 'Inventory', 'url': 'web.manage_inventory', 'icon': 'fas fa-boxes'})

        if features.get('campaigns'):
            business_menu.append({'name': 'Campaigns', 'url': 'web.campaign_management', 'icon': 'fas fa-rocket'})

        if features.get('budgets'):
            business_menu.append({'name': 'Budgets', 'url': 'web.manage_budgets', 'icon': 'fas fa-calculator'})

        if features.get('suppliers'):
            business_menu.append({'name': 'Suppliers', 'url': 'web.manage_suppliers', 'icon': 'fas fa-truck'})

        business_menu.append({'name': 'User Management', 'url': 'web.manage_users', 'icon': 'fas fa-users'})

        menu_items.append({
            'name': 'Business',
            'items': business_menu,
            'icon': 'fas fa-building'
        })

        # Tools submenu
        tools_menu = []
        tools_menu.append({'name': 'Tax Calculator', 'url': 'web.tax_calculator', 'icon': 'fas fa-calculator'})
        tools_menu.append({'name': 'Currency Converter', 'url': 'web.currency_converter', 'icon': 'fas fa-exchange-alt'})

        if features.get('customers'):
            tools_menu.append({'name': 'CRM', 'url': 'web.manage_customers', 'icon': 'fas fa-users'})

        if features.get('sales_goals'):
            tools_menu.append({'name': 'Sales Goals', 'url': 'web.manage_sales_goals', 'icon': 'fas fa-target'})

        if features.get('invoices'):
            tools_menu.append({'name': 'Invoices', 'url': 'web.manage_invoices', 'icon': 'fas fa-file-invoice-dollar'})

        if features.get('projects'):
            tools_menu.append({'name': 'Projects', 'url': 'web.manage_projects', 'icon': 'fas fa-project-diagram'})

        menu_items.append({
            'name': 'Tools',
            'items': tools_menu,
            'icon': 'fas fa-tools'
        })

        # Reports menu
        if features.get('reports'):
            menu_items.append({
                'name': 'Reports',
                'url': 'web.business_reports',
                'icon': 'fas fa-chart-bar'
            })

        return menu_items

    @staticmethod
    def get_recommended_modules(business_type_name):
        """Get recommended additional modules for a business type"""
        recommendations = {
            'Retail Store': [
                'Advanced inventory management',
                'Customer loyalty programs',
                'Point of sale integration',
                'Barcode scanning'
            ],
            'Restaurant/Cafe': [
                'Recipe cost calculation',
                'Table reservation system',
                'Food waste tracking',
                'Menu digitalization'
            ],
            'Service Business': [
                'Appointment scheduling',
                'Customer feedback system',
                'Service contract management',
                'Time tracking integration'
            ],
            'Manufacturing': [
                'Production planning',
                'Quality control tracking',
                'Supply chain optimization',
                'Equipment maintenance'
            ],
            'E-commerce': [
                'Online store integration',
                'Shipping management',
                'Multi-channel sales tracking',
                'Customer behavior analytics'
            ],
            'Construction': [
                'Project timeline management',
                'Material procurement tracking',
                'Safety compliance monitoring',
                'Subcontractor management'
            ],
            'Marketing Agency': [
                'Campaign ROI tracking',
                'Client portal',
                'Content management system',
                'Social media integration'
            ],
            'Consulting Firm': [
                'Project milestone tracking',
                'Knowledge base',
                'Client feedback system',
                'Proposal generation'
            ],
            'Healthcare': [
                'Patient management system',
                'Appointment scheduling',
                'Medical record tracking',
                'Insurance billing'
            ],
            'Education': [
                'Student information system',
                'Course management',
                'Attendance tracking',
                'Grade management'
            ]
        }

        return recommendations.get(business_type_name, [])

    @staticmethod
    def get_business_type_info(business_id):
        """Get business type information and recommendations"""
        business = Business.query.get(business_id)
        if not business or not business.business_type_obj:
            return None

        bt = business.business_type_obj
        features = BusinessTypeService.get_business_features(business_id)
        recommendations = BusinessTypeService.get_recommended_modules(bt.name)

        return {
            'business_type': bt,
            'enabled_features': features,
            'recommendations': recommendations,
            'feature_count': sum(features.values())
        }
