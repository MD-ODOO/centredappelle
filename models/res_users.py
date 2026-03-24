from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    event_ids = fields.One2many(
        'calendar.event',
        'conseiller_id',
        string="RDV"
    )

    monthly_target = fields.Integer(
        string="Objectif mensuel RDV",
        default=20
    )

    rdv_month_count = fields.Integer(
        compute="_compute_rdv_month"
    )

    def _compute_rdv_month(self):
        today = fields.Date.today()
        month_start = today.replace(day=1)

        for user in self:
            count = self.env['calendar.event'].search_count([
                ('conseiller_id', '=', user.id),
                ('create_date', '>=', month_start)
            ])
            user.rdv_month_count = count