/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class ExecutiveDashboardBI extends Component {

    setup(){

        this.orm = useService("orm");

        this.state = useState({
            data: {}
        });

        this.charts = {};

        onWillStart(async () => {

            const result = await this.orm.call(
                "oui.campaign",
                "get_dashboard_bi",
                []
            );

            this.state.data = result;

            setTimeout(()=>this.renderCharts(),200);
        });
    }

    renderCharts(){

        // PIPELINE

        const pipeline = document.getElementById("pipelineChart");

        if(pipeline){

            this.charts.pipeline = new Chart(pipeline,{
                type:"doughnut",
                data:{
                    labels:this.state.data.pipeline.map(d=>d.stage),
                    datasets:[{
                        data:this.state.data.pipeline.map(d=>d.value)
                    }]
                }
            });
        }

        // CONSEILLERS

        const cons = document.getElementById("conseillerChart");

        if(cons){

            this.charts.cons = new Chart(cons,{
                type:"bar",
                data:{
                    labels:this.state.data.conseillers.map(d=>d.name),
                    datasets:[{
                        data:this.state.data.conseillers.map(d=>d.value)
                    }]
                }
            });
        }

        // EVOLUTION

        const evo = document.getElementById("evolutionChart");

        if(evo){

            this.charts.evo = new Chart(evo,{
                type:"line",
                data:{
                    labels:this.state.data.monthly.map(d=>d.month),
                    datasets:[{
                        label:"RDV",
                        data:this.state.data.monthly.map(d=>d.value)
                    }]
                }
            });
        }

    }

}

ExecutiveDashboardBI.template = "ExecutiveDashboardBI";

registry.category("actions").add(
    "executive_dashboard_bi",
    ExecutiveDashboardBI
);