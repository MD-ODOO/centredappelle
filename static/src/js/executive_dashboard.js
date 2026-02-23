/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { onMounted } from "@odoo/owl";

export class ExecutiveDashboard extends Component {

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            period: "month",
            loading: true,
            data: {
                global: {},
                conseillers: [],
                campagnes: [],
                is_admin: false,
            }
        });

        this.changePeriod = this.changePeriod.bind(this);
        this.loadData = this.loadData.bind(this);

        onWillStart(async () => {
            await this.loadData();
        });

        onMounted(() => {
            this.renderCharts();
        });
        
    }

    async loadData() {
        this.state.loading = true;
        setTimeout(() => this.renderCharts(), 100);

        try {
            const result = await this.orm.call(
                "oui.campaign",
                "get_executive_dashboard_data",
                [this.state.period]
            );

            this.state.data = result;
        } catch (error) {
            this.notification.add("Erreur lors du chargement du dashboard", {
                type: "danger",
            });
            console.error(error);
        }

        this.state.loading = false;
    }

    async changePeriod(ev) {
        const period = ev.target.value;
        if (this.state.period === period) return;
        this.state.period = period;
        await this.loadData();
    }

    renderCharts() {

        if (!this.state.data) return;
    
        // Pie Campagnes
        const pieCampCtx = document.getElementById("pieCampaigns");
        if (pieCampCtx) {
            new Chart(pieCampCtx, {
                type: "pie",
                data: {
                    labels: this.state.data.pie_campaigns.map(d => d.name),
                    datasets: [{
                        data: this.state.data.pie_campaigns.map(d => d.value)
                    }]
                }
            });
        }
    
        // Pie Conseillers
        const pieConsCtx = document.getElementById("pieConseillers");
        if (pieConsCtx) {
            new Chart(pieConsCtx, {
                type: "pie",
                data: {
                    labels: this.state.data.pie_conseillers.map(d => d.name),
                    datasets: [{
                        data: this.state.data.pie_conseillers.map(d => d.value)
                    }]
                }
            });
        }
    
        // Bar Performance
        const barCtx = document.getElementById("barPerformance");
        if (barCtx) {
            new Chart(barCtx, {
                type: "bar",
                data: {
                    labels: this.state.data.bar_performance.map(d => d.name),
                    datasets: [{
                        label: "% Exploitation",
                        data: this.state.data.bar_performance.map(d => d.taux)
                    }]
                }
            });
        }
    
        // Evolution mensuelle
        const lineCtx = document.getElementById("monthlyEvolution");
        if (lineCtx) {
            new Chart(lineCtx, {
                type: "line",
                data: {
                    labels: this.state.data.monthly_evolution.map(d => d.month),
                    datasets: [{
                        label: "RDV",
                        data: this.state.data.monthly_evolution.map(d => d.value)
                    }]
                }
            });
        }
    }

    openConseiller(id) {
        if (!id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.users",
            res_id: id,
            views: [[false,"form"]]
        });
    }

    openCampaign(id) {
        if (!id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "oui.campaign",
            res_id: id,
            views: [[false,"form"]]
        });
    }

    getPerformanceClass(taux){
        if(taux>=80) return "badge-green";
        if(taux>=50) return "badge-orange";
        return "badge-red";
    }
}

ExecutiveDashboard.template = "ExecutiveDashboard";
registry.category("actions").add("executive_dashboard", ExecutiveDashboard);