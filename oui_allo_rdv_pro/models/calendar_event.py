from odoo import models, fields, api,_
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError



class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    campaign_id = fields.Many2one('oui.campaign', string="Campagne",index=True)
    conseiller_id = fields.Many2many('res.users', string="Conseiller", required=True)
    campaign_manager_id = fields.Many2one(
        'res.users',
        string="Responsable de campagne"
        )
    
    
    color = fields.Integer(
    string="Couleur",
    related="stage_id.color",
    store=True,
    readonly=True

    )
  

    priority_level = fields.Selection([
    ('low', 'Faible'),
    ('normal', 'Normal'),
    ('high', 'Urgent'),
], default='normal')
    
    is_overdue = fields.Boolean(
    compute="_compute_is_overdue",
    store=True
    )

    @api.depends('start', 'stage_id.is_done')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_overdue = (
                rec.start and
                rec.start < now and
                not rec.stage_id.is_done
            )

    stage_id = fields.Many2one(
    'rdv.stage',
    string="Étape",
    group_expand='_read_group_stage_ids',
    tracking=True,
    index=True,
    store=True,
    default=lambda self: self.env['rdv.stage'].search([], order="sequence asc", limit=1)
)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['rdv.stage'].search([], order="sequence asc")
    

    
    delay_days = fields.Integer(
    compute="_compute_delay_days",
    store=False)

    def _compute_delay_days(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.start:
                rec.delay_days = (now - rec.start).days
            else:
                rec.delay_days = 0
    
    def write(self, vals):

        if 'stage_id' in vals:
            new_stage = self.env['rdv.stage'].browse(vals['stage_id'])

            for rec in self:

                # 1️⃣ Bloquer si campagne fermée
                if rec.campaign_id and rec.campaign_id.state == 'closed':
                    raise ValidationError(
                        "Impossible de modifier l'étape d'une campagne fermée."
                    )

                # 2️⃣ Bloquer si volume dépassé
                if (
                        rec.campaign_id and
                        new_stage.is_done and
                        rec.campaign_id.rdv_realised >= rec.campaign_id.total_volume
                    ):
                    raise ValidationError(
                        "Le volume contractuel est atteint."
                    )

        return super().write(vals)
    
    def _cron_check_overdue(self):

        overdue_stage = self.env['rdv.stage'].search(
            [('name', '=', 'En retard')],
            limit=1
        )

        if not overdue_stage:
            return

        now = fields.Datetime.now()

        events = self.search([
            ('start', '<', now),
            ('stage_id.is_done', '=', False)
        ])

        events.write({'stage_id': overdue_stage.id})
    
    @api.constrains('start', 'campaign_id')
    def _check_campaign_period(self):
        for rec in self:
            if rec.campaign_id:
                campaign = rec.campaign_id
                # event_date = rec.start.date() if rec.start else False

                if rec.start and campaign.date_start:
                    if rec.start.date() < campaign.date_start:
                        raise ValidationError("Le RDV est avant le début de la campagne.")

                if rec.start and campaign.date_end:
                    if rec.start.date() > campaign.date_end:
                        raise ValidationError("Le RDV est après la fin de la campagne.")
    
    @api.constrains('start', 'stop', 'conseiller_id', 'partner_id')
    def _check_planning_conflicts(self):

        for rec in self:

            if not rec.start or not rec.stop:
                continue

            domain = [
                ('id', '!=', rec.id),
                ('start', '<', rec.stop),
                ('stop', '>', rec.start),
            ]

            conflicts = self.search(domain, limit=1)


            for event in conflicts:

                # 1️⃣ Conflit conseiller
                if rec.conseiller_id and event.conseiller_id:
                    if set(rec.conseiller_id.ids) & set(event.conseiller_id.ids):
                        raise ValidationError(
                            "Un conseiller a déjà un RDV sur ce créneau."
                        )

                # 2️⃣ Conflit client
                if rec.partner_id and rec.partner_id == event.partner_id:
                    raise ValidationError(
                        "Ce client a déjà un RDV sur ce créneau."
                    )

                # 3️⃣ Conflit participants (sécurité supplémentaire)
                if set(rec.partner_ids.ids) & set(event.partner_ids.ids):
                    raise ValidationError(
                        "Un participant est déjà occupé sur ce créneau."
                    )
                
    _sql_constraints = [
    ('check_dates', 'CHECK(stop > start)', 'La date de fin doit être après le début.')
]
