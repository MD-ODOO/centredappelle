from datetime import timedelta

from odoo import api, fields, models


class CampaignGenerateRdvWizard(models.TransientModel):
    _name = 'campaign.generate.rdv.wizard'
    _description = 'Génération RDV depuis Campagne'

    campaign_id = fields.Many2one('oui.campaign', required=True)
    partner_id = fields.Many2one('res.partner', string="Client")
    responsable_id = fields.Many2one('res.users', string="Responsable")
    conseiller_ids = fields.Many2many(
        'res.users',
        string="Conseillers",
        
    )
   
    rdv_line_ids = fields.One2many(
        'campaign.generate.rdv.line',
        'wizard_id',
        string="Dates RDV",
    )

   

    def action_generate_rdv(self):

        calendar_event_model = self.env['calendar.event']

        for line in self.rdv_line_ids:

            if not line.conseiller_ids:
                continue

            calendar_event_model.create({
                'name': self.campaign_id.name,
                'start': line.start_datetime,
                'stop': line.start_datetime + timedelta(hours=line.duration),
                'campaign_id': self.campaign_id.id,
                'campaign_manager_id': self.responsable_id.id,
                'conseiller_id': line.conseiller_ids.id,
                'partner_id': self.partner_id.id,
                'partner_ids': [(6, 0, [self.partner_id.id])],
            })

        return {'type': 'ir.actions.act_window_close'}

class CampaignGenerateRdvLine(models.TransientModel):
    _name = 'campaign.generate.rdv.line'
    _description = 'Ligne RDV Wizard'

    wizard_id = fields.Many2one('campaign.generate.rdv.wizard')
    start_datetime = fields.Datetime("Début RDV", required=True)
    conseiller_ids = fields.Many2one(
    'res.users',
    string="Conseiller",
    required=True,
    domain="[('id', 'in', allowed_conseillers)]"
)

    allowed_conseillers = fields.Many2many(
    'res.users',
    compute='_compute_allowed_conseillers',
)
    duration = fields.Float("Durée (heures)", default=1.0)


    @api.depends('wizard_id.conseiller_ids')
    def _compute_allowed_conseillers(self):
        for rec in self:
            if rec.wizard_id and rec.wizard_id.conseiller_ids:
                rec.allowed_conseillers = rec.wizard_id.conseiller_ids
            else:
                rec.allowed_conseillers = False

  
