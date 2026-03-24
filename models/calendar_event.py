from odoo import models, fields, api,_
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError,UserError
from datetime import timedelta




class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    campaign_id = fields.Many2one('oui.campaign', string="Campagne",index=True)
    conseiller_id = fields.Many2one('res.users', string="Conseiller", required=True)
    campaign_manager_id = fields.Many2one(
        'res.users',
        string="Responsable de campagne"
        )
    
    partner_id = fields.Many2one(
    'res.partner',
    string="Client"
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
    default=lambda self: self.env['rdv.stage'].search([], order="sequence asc", limit=1).id
)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['rdv.stage'].search([], order="sequence asc")
    

    
    delay_days = fields.Integer(
    compute="_compute_delay_days",
    store=False)

    is_absent = fields.Boolean(default=False)
    auto_validated = fields.Boolean(default=False)
    recall_date_1 = fields.Datetime()
    recall_date_2 = fields.Datetime()

    def _send_absent_notification(self, days_after):
        """Envoi notification aux conseillers et clients directement depuis Python"""
        for rdv in self:
            # Format date rendez-vous
            rdv_date = fields.Datetime.to_string(rdv.start)
            subject = f"Rendez-vous absent – J+{days_after}"
            body = f"Votre rendez-vous du {rdv_date} n'a pas été à date prévue."

            # Destinataires : clients uniquement (tu peux ajouter conseillers si besoin)
            email_to = ','.join(filter(None, [p.email for p in rdv.partner_ids]))

            if email_to:
                self.env['mail.mail'].create({
                    'subject': subject,
                    'body_html': body,
                    'email_to': email_to,
                    'auto_delete': True,
                }).send()

    def _process_rdv_cron(self):
        """Automatisation RDV – à lancer via cron"""
        now = fields.Datetime.now()

        stage_exploite = self.env.ref('oui_allo_rdv_pro.stage_exploite')
        stage_absent = self.env.ref('oui_allo_rdv_pro.stage_absent')
        stage_recycle = self.env.ref('oui_allo_rdv_pro.stage_recycle')

        # 1️⃣ RDV passés +24h qui ne sont pas exploités ni absents → Auto Valide
        rdv_to_validate = self.search([
            ('stop', '<=', now - timedelta(hours=24)),
            ('stage_id', 'not in', [stage_exploite.id, stage_absent.id])
        ])
        for rdv in rdv_to_validate:
            rdv.stage_id = stage_exploite
            rdv.auto_validated = True

        # 2️⃣ RDV absents → Recyclage et planification notifications
        rdv_absent = self.search([
            ('stage_id', '=', stage_absent.id),
        ])
        for rdv in rdv_absent:
            if not rdv.recall_date_1:
                rdv.stage_id = stage_recycle
                rdv.recall_date_1 = now + timedelta(days=1)
                rdv.recall_date_2 = now + timedelta(days=2)
                # Notification J+1
                rdv._send_absent_notification(days_after=1)
            elif rdv.recall_date_1 <= now < rdv.recall_date_2:
                # Notification J+2
                rdv._send_absent_notification(days_after=2)

        return True
    
    def action_mark_absent(self):
        stage_absent = self.env.ref('oui_allo_rdv_pro.stage_absent')
        stage_exploite = self.env.ref('oui_allo_rdv_pro.stage_exploite')
        stage_recycle = self.env.ref('oui_allo_rdv_pro.stage_recycle')

        for event in self:

            if event.stage_id == stage_exploite:
                raise UserError("Ce rendez-vous est déjà exploité.")

            if event.stage_id == stage_absent:
                raise UserError("Ce rendez-vous est déjà marqué absent.")

            event.stage_id = stage_absent
            event.is_absent = True
            event.recall_date_1 = fields.Datetime.now() + timedelta(days=1)
            event.recall_date_2 = fields.Datetime.now() + timedelta(days=2)

    @api.depends('start')
    def _compute_delay_days(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.start:
                delta = now - rec.start
                rec.delay_days = int(delta.total_seconds() // 86400)
            else:
                rec.delay_days = 0
    
    def write(self, vals):


        for rec in self:

                # 1️⃣ Bloquer si campagne fermée
            if 'stage_id' in vals and rec.campaign_id.state == 'closed':
                raise ValidationError(
                        "Impossible de modifier l'étape d'une campagne fermée."
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
    
    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            campaign_id = vals.get('campaign_id')
            if campaign_id:
                campaign = self.env['oui.campaign'].browse(campaign_id)

                total_rdv = self.search_count([
                    ('campaign_id', '=', campaign.id)
                ])

                if total_rdv >= campaign.total_volume:
                    raise ValidationError(
                        f"Volume contractuel atteint.\n"
                        f"Autorisé : {campaign.total_volume}\n"
                        f"Déjà planifiés : {total_rdv}"
                    )

        return super().create(vals_list)

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

            conflicts = self.search(domain)


            for event in conflicts:
 
                # 1️⃣ Conflit conseiller
                if rec.conseiller_id and event.conseiller_id:
                    if rec.conseiller_id.id == event.conseiller_id.id:
                        raise ValidationError(
                            "Un conseiller a déjà un RDV sur ce créneau."
                        )

                # 2️⃣ Conflit client
                if rec.partner_id and rec.partner_id == event.partner_id:
                    raise ValidationError(
                        "Ce client a déjà un RDV sur ce créneau."
                    )

                # 3️⃣ Conflit participants (sécurité supplémentaire)
                if rec.conseiller_id and event.conseiller_id:
                    if rec.conseiller_id.id == event.conseiller_id.id:
                        raise ValidationError(
                            "Un participant est déjà occupé sur ce créneau."
                        )
                
    _sql_constraints = [
    ('check_dates', 'CHECK(stop > start)', 'La date de fin doit être après le début.')
]
    def init(self):
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_campaign
            ON calendar_event (campaign_id);

            CREATE INDEX IF NOT EXISTS idx_event_stage
            ON calendar_event (stage_id);

            CREATE INDEX IF NOT EXISTS idx_event_start
            ON calendar_event (start);

            CREATE INDEX IF NOT EXISTS idx_event_conseiller
            ON calendar_event (conseiller_id);
        """)