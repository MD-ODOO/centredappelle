
{
    'name': 'Oui Allo RDV Pro',
    'version': '19.0.1.0.0',
    'author': 'Oui Allo',
    'depends': ['base','calendar', 'crm', 'mail', 'portal'],
    'sequence':'1',
    'data': [
        'security/security.xml',
         'security/ir.model.access.csv',
        # 'demo/cron.xml',
        'views/campaign_views.xml',
        'views/rdv_views.xml',
        'views/executive_dashboard_action.xml',
        'views/conseiller_views.xml',
        'wizard/compagne_wizard_view.xml',
        'views/stage.xml',
        'views/menu.xml',
    ],
    'demo': [
    ],
     'assets': {
        'web.assets_backend': [
            'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js',
            'oui_allo_rdv_pro/static/src/css/executive_dashboard.css',
            'oui_allo_rdv_pro/static/src/js/executive_dashboard.js',
            'oui_allo_rdv_pro/static/src/xml/executive_dashboard.xml',
        ],
    },
     
    
    'installable': True,
    'application': True,
}
