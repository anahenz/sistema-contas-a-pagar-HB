from collections import defaultdict
from decimal import Decimal
from xml.sax.saxutils import escape
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from app.utils.formatting import money, fmt_date


class ReportService:
    def __init__(self, finance):
        self.finance = finance

    def report(self, start, end):
        if start > end:
            raise ValueError("A data inicial não pode ser posterior à final.")
        accounts = [
            a
            for a in self.finance.accounts(start=start, end=end)
            if a["status"] != "Cancelada"
        ]
        history = self.finance.history(start, end, False)
        pending = [a for a in accounts if a["status"] != "Paga"]
        summary = [
            ["Indicador", "Valor"],
            [
                "Total pago no período (data do pagamento)",
                money(sum(a["payment"]["valor_centavos"] for a in history)),
            ],
            [
                "Total pendente (vencimentos no período)",
                money(sum(a["valor_centavos"] for a in pending)),
            ],
            [
                "Total vencido (vencimentos no período)",
                money(
                    sum(
                        a["valor_centavos"] for a in pending if a["status"] == "Vencida"
                    )
                ),
            ],
        ]
        groups = {}
        for field, title in [
            ("condominio", "Gastos por condomínio"),
            ("categoria", "Gastos por categoria"),
            ("fornecedor", "Gastos por fornecedor"),
        ]:
            values = defaultdict(lambda: [0, 0])
            for a in accounts:
                values[a[field]][0] += a["valor_centavos"]
            for a in history:
                values[a[field]][1] += a["payment"]["valor_centavos"]
            groups[title] = [
                ["Nome", "Lançado por vencimento", "Pago por pagamento"]
            ] + [[k, money(v[0]), money(v[1])] for k, v in sorted(values.items())]
        monthly = defaultdict(lambda: [0, 0])
        for a in accounts:
            monthly[a["data_vencimento"].strftime("%Y-%m")][0] += a["valor_centavos"]
        for a in history:
            monthly[a["payment"]["data_pagamento"].strftime("%Y-%m")][1] += a[
                "payment"
            ]["valor_centavos"]
        groups["Histórico mensal"] = [
            ["Mês", "Lançado por vencimento", "Pago por pagamento"]
        ] + [[k, money(v[0]), money(v[1])] for k, v in sorted(monthly.items())]
        detail = [
            [
                "Condomínio",
                "Despesa",
                "Categoria",
                "Fornecedor",
                "Valor",
                "Vencimento",
                "Status",
            ]
        ] + [
            [
                a["condominio"],
                a["nome"],
                a["categoria"],
                a["fornecedor"],
                money(a["valor_centavos"]),
                fmt_date(a["data_vencimento"]),
                a["status"],
            ]
            for a in accounts
        ]
        payments = [
            [
                "Condomínio",
                "Despesa",
                "Pago",
                "Data do pagamento",
                "Forma",
                "Comprovante",
            ]
        ] + [
            [
                a["condominio"],
                a["nome"],
                money(a["payment"]["valor_centavos"]),
                fmt_date(a["payment"]["data_pagamento"]),
                a["payment"]["forma_pagamento"],
                a["payment"]["comprovante"],
            ]
            for a in history
        ]
        return {"Resumo": summary, **groups, "Contas": detail, "Pagamentos": payments}

    def excel(self, path, start, end):
        data = self.report(start, end)
        wb = Workbook()
        wb.remove(wb.active)
        for title, rows in data.items():
            ws = wb.create_sheet(title[:31])
            ws.append([f"Período: {fmt_date(start)} a {fmt_date(end)}"])
            for row in rows:
                # Avoid formula execution when a user enters text starting with =, +, -, @.
                ws.append(
                    [
                        ("'" + str(v)) if str(v).startswith(("=", "+", "-", "@")) else v
                        for v in row
                    ]
                )
            for cell in ws[2]:
                cell.fill = PatternFill("solid", fgColor="1E3A5F")
                cell.font = Font(color="FFFFFF", bold=True)
            ws.freeze_panes = "A3"
            ws.auto_filter.ref = (
                f"A2:{ws.cell(max(2,ws.max_row),len(rows[0])).coordinate}"
            )
            for column in ws.columns:
                length = (
                    max(len(str(c.value or "")) for c in column[1:])
                    if len(column) > 1
                    else 20
                )
                ws.column_dimensions[column[0].column_letter].width = min(
                    48, max(18, length + 2)
                )
            # Convert currency and dates to native spreadsheet values.
            for row in ws.iter_rows(min_row=3):
                for c in row:
                    if isinstance(c.value, str) and c.value.startswith("R$ "):
                        c.value = float(
                            Decimal(c.value[3:].replace(".", "").replace(",", "."))
                        )
                        c.number_format = '"R$" #,##0.00'
            ws.sheet_view.showGridLines = False
        wb.save(path)

    def pdf(self, path, start, end):
        styles = getSampleStyleSheet()
        styles["Normal"].fontSize = 8
        styles["Normal"].leading = 11
        story = [
            Paragraph("ContasPagar | Relatório financeiro", styles["Title"]),
            Paragraph(
                f"Período: {fmt_date(start)} a {fmt_date(end)}", styles["Normal"]
            ),
            Spacer(1, 15),
        ]
        width = landscape(A4)[0] - 64
        for title, rows in self.report(start, end).items():
            story.extend([Paragraph(title, styles["Heading2"]), Spacer(1, 6)])
            wrapped = [
                [Paragraph(escape(str(v)), styles["Normal"]) for v in row]
                for row in rows
            ]
            table = Table(
                wrapped,
                colWidths=[width / len(rows[0])] * len(rows[0]),
                repeatRows=1,
                hAlign="LEFT",
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF8")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#2563EB")),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#F5F7FA")],
                        ),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                )
            )
            story.extend([table, Spacer(1, 16)])

        def footer(canvas, doc):
            canvas.setFont("Helvetica", 8)
            canvas.drawString(
                32,
                18,
                "ContasPagar • Valores em reais • Pagamentos estornados excluídos",
            )
            canvas.drawRightString(landscape(A4)[0] - 32, 18, f"Página {doc.page}")

        SimpleDocTemplate(
            str(path),
            pagesize=landscape(A4),
            rightMargin=32,
            leftMargin=32,
            topMargin=30,
            bottomMargin=35,
        ).build(story, onFirstPage=footer, onLaterPages=footer)
