# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Runtime internationalization for the plugin.

The plugin keeps Portuguese source messages for backward compatibility and
translates them to English when the QGIS interface locale is not Brazilian
Portuguese. English is therefore the guaranteed fallback language.
"""

from __future__ import annotations

import os
import re
from typing import Optional


_PT_BR = "pt_BR"
_EN = "en"
_requested_locale = "en"
_active_locale = _EN


# Exact catalog. Values are the English fallback strings.
PT_TO_EN = {
    # Plugin shell
    "Visualizador de Séries Temporais InSAR": "InSAR Time Series Viewer",
    "Visualizador de Séries Temporais": "Time Series Viewer",
    "Séries Temporais InSAR": "InSAR Time Series",
    "&Visualizador de Séries Temporais": "&Time Series Viewer",
    "Abre o painel de séries temporais para camadas pontuais InSAR": "Open the time-series panel for InSAR point layers",
    "Não foi possível criar o painel do plugin.": "The plugin panel could not be created.",
    "Ajuda do Visualizador de Séries Temporais InSAR": "InSAR Time Series Viewer Help",
    "Abre a documentação do plugin": "Open the plugin documentation",
    # Header and state
    "Camada:": "Layer:",
    "Atualizar": "Refresh",
    "Atualizar a lista de camadas compatíveis": "Refresh the list of compatible layers",
    "Configurar campos...": "Configure fields...",
    "Configurar campos": "Configure fields",
    "Configurar campos da camada": "Configure layer fields",
    "Configurar mapeamento manual dos campos da camada": "Configure manual field mapping for the layer",
    "Selecione uma camada pontual antes de configurar campos.": "Select a point layer before configuring fields.",
    "O mapeamento salvo não pôde ser lido e será ignorado: {error}": "The saved mapping could not be read and will be ignored: {error}",
    "Mapeamento manual removido da camada {layer}.": "Manual mapping removed from layer {layer}.",
    "Mapeamento de campos salvo para {layer}.": "Field mapping saved for {layer}.",
    "Configure campos opcionais da camada selecionada. Campos deixados como automáticos continuarão sendo detectados por aliases. As datas ainda usam campos DYYYYMMDD.": "Configure optional fields for the selected layer. Fields left as automatic will continue to be detected by aliases. Dates still use DYYYYMMDD fields.",
    "Identificador:": "Identifier:",
    "Campo de componente:": "Component field:",
    "Velocidade:": "Velocity:",
    "Incerteza da velocidade:": "Velocity uncertainty:",
    "Órbita/passagem:": "Orbit/pass:",
    "Unidade:": "Unit:",
    "Sentinela NoData:": "NoData sentinel:",
    "Genérica": "Generic",
    "Campos temporais:": "Temporal fields:",
    "Nenhum campo temporal DYYYYMMDD detectado.": "No DYYYYMMDD temporal fields detected.",
    "{count} campos DYYYYMMDD detectados. Cobertura: {first_date} a {last_date}. Campos: {fields}.": "{count} DYYYYMMDD fields detected. Coverage: {first_date} to {last_date}. Fields: {fields}.",
    "{count} campos DYYYYMMDD detectados. Cobertura: {first_date} a {last_date}. Primeiro campo: {first_field}; último campo: {last_field}. Primeiros: {first_names}. Últimos: {last_names}.": "{count} DYYYYMMDD fields detected. Coverage: {first_date} to {last_date}. First field: {first_field}; last field: {last_field}. First: {first_names}. Last: {last_names}.",
    "Nesta versão, campos temporais customizados ainda não são editados neste diálogo. O leitor usa automaticamente campos DYYYYMMDD.": "In this version, custom temporal fields are not edited in this dialog yet. The reader automatically uses DYYYYMMDD fields.",
    "Limpar mapeamento salvo": "Clear saved mapping",
    "Modo dos campos temporais:": "Temporal field mode:",
    "Automático: detectar DYYYYMMDD": "Automatic: detect DYYYYMMDD",
    "Manual: usar tabela abaixo": "Manual: use table below",
    "Usar": "Use",
    "Campo": "Field",
    "Data": "Date",
    "No modo manual, marque os campos temporais e ajuste suas datas. No modo automático, o leitor usa campos DYYYYMMDD.": "In manual mode, check temporal fields and adjust their dates. In automatic mode, the reader uses DYYYYMMDD fields.",
    "Filtrar campos...": "Filter fields...",
    "Selecionar campos DYYYYMMDD": "Select DYYYYMMDD fields",
    "Limpar seleção temporal": "Clear temporal selection",
    "Modo:": "Mode:",
    "Série única": "Single series",
    "Séries sobrepostas": "Overlaid series",
    "Séries separadas": "Separate series",
    "Média das séries": "Series mean",
    "Médias por polígonos — sobrepostas": "Polygon means — overlaid",
    "Médias por polígonos — separadas": "Polygon means — separate",
    "Configurações": "Settings",
    "Mostrar ou ocultar as configurações ao lado do gráfico": "Show or hide the settings beside the chart",
    "Ocultar configurações": "Hide settings",
    "Mostrar configurações": "Show settings",
    "Nenhuma camada compatível selecionada.": "No compatible layer selected.",
    "Nenhuma camada pontual compatível foi encontrada no projeto.": "No compatible point layer was found in the project.",
    "Selecione uma camada InSAR compatível.": "Select a compatible InSAR layer.",
    "A camada escolhida não está mais disponível.": "The selected layer is no longer available.",
    "Camada incompatível.": "Incompatible layer.",
    "— selecione uma camada —": "— select a layer —",
    "0 selecionadas": "0 selected",
    "0 médias poligonais": "0 polygon means",
    "Aproximar do ponto": "Zoom to point",
    "Aproxima o mapa para a feição atualmente exibida no gráfico": "Zooms the map to the feature currently shown in the chart",
    "Limpar seleção": "Clear selection",
    "Remove a seleção atual da camada pontual": "Clears the current selection from the point layer",
    "Nenhum ponto válido está disponível para aproximar.": "No valid point is available to zoom to.",
    "Não foi possível reprojetar o ponto para o mapa: {error}": "The point could not be reprojected to the map: {error}",
    "Mapa aproximado para FID {fid}.": "Map zoomed to FID {fid}.",
    # Information panel
    "Ponto/série:": "Point/series:",
    "Componente:": "Component:",
    "Desloc. acumulado:": "Cumulative displacement:",
    "Cobertura válida:": "Valid coverage:",
    "Propriedades adicionais:": "Additional properties:",
    "Configurações do gráfico": "Chart settings",
    "Ocultar": "Hide",
    "Recolher o painel de configurações": "Collapse the settings panel",
    # Orbit
    "Automática": "Automatic",
    "Automático": "Automatic",
    "Ascendente": "Ascending",
    "Descendente": "Descending",
    "Não especificada": "Unspecified",
    "Direção desta camada:": "Direction for this layer:",
    "No modo automático, a direção é inferida por tokens A/D ou ASC/DESC no nome ou caminho da camada.": "In automatic mode, direction is inferred from A/D or ASC/DESC tokens in the layer name or path.",
    # Spatial selection
    "Seleção por área": "Area selection",
    "Desenhar área no mapa": "Draw area on map",
    "Desenhando área...": "Drawing area...",
    "Clique com o botão esquerdo para adicionar vértices; botão direito conclui e Esc cancela": "Left-click to add vertices; right-click to finish and Esc to cancel",
    "Limpar área": "Clear area",
    "Remove o polígono temporário do mapa sem alterar a seleção de pontos": "Remove the temporary polygon from the map without changing the point selection",
    "Desenho: botão esquerdo adiciona vértices, botão direito conclui e Esc cancela.": "Drawing: left-click adds vertices, right-click finishes, and Esc cancels.",
    "Camada poligonal:": "Polygon layer:",
    "Usar polígono selecionado": "Use selected polygon",
    "Substituir seleção": "Replace selection",
    "Adicionar à seleção": "Add to selection",
    "Remover da seleção": "Remove from selection",
    "Operação:": "Operation:",
    "{description}: {found} ponto(s) encontrado(s); {operation}; {selected} ponto(s) selecionado(s) ao final.": "{description}: {found} point(s) found; {operation}; {selected} point(s) selected in total.",
    "Nenhuma área aplicada nesta sessão.": "No area has been applied in this session.",
    "Adicione ao menos três vértices. Botão direito conclui; Esc cancela.": "Add at least three vertices. Right-click to finish; Esc to cancel.",
    "Desenho da área cancelado.": "Area drawing canceled.",
    "Área removida do mapa. A seleção de pontos foi mantida.": "Area removed from the map. The point selection was kept.",
    "Escolha uma camada poligonal válida.": "Choose a valid polygon layer.",
    "Selecione exatamente uma feição na camada poligonal.": "Select exactly one feature in the polygon layer.",
    "A feição poligonal selecionada não possui geometria válida.": "The selected polygon feature does not have valid geometry.",
    "Construindo índice espacial da camada de pontos...": "Building the point-layer spatial index...",
    # Polygon means
    "Médias por polígonos": "Polygon means",
    "Todos os polígonos": "All polygons",
    "Somente selecionados": "Selected only",
    "Processar:": "Process:",
    "Campo do nome:": "Name field:",
    "Médias sobrepostas": "Overlaid means",
    "Médias separadas": "Separate means",
    "Visualização:": "Display:",
    "Calcular médias por polígonos": "Calculate polygon means",
    "Voltar aos pontos selecionados": "Return to selected points",
    "Usa a camada poligonal escolhida em Seleção por área. Cada polígono gera uma média independente; polígonos sobrepostos podem compartilhar pontos.": "Uses the polygon layer selected under Area selection. Each polygon produces an independent mean; overlapping polygons may share points.",
    "Nenhuma média poligonal calculada nesta sessão.": "No polygon mean has been calculated in this session.",
    "Nenhuma média poligonal calculada para esta camada.": "No polygon mean has been calculated for this layer.",
    "— sem campo: usar Média de X pontos —": "— no field: use Mean of X points —",
    "Médias poligonais removidas; exibindo a seleção de pontos.": "Polygon means removed; displaying the selected points.",
    "Os pontos foram alterados; recalcule as médias por polígonos.": "The points changed; recalculate the polygon means.",
    "Os resultados poligonais são calculados sob demanda e não alteram a seleção dos pontos.": "Polygon results are calculated on demand and do not alter the point selection.",
    # Appearance
    "Aparência das séries": "Series appearance",
    "Mostrar linhas": "Show lines",
    "Mostrar marcadores": "Show markers",
    "Mostrar referência em zero": "Show zero reference",
    "Mostrar legenda em séries sobrepostas e na média": "Show legend for overlaid series and means",
    "Mostrar dados ao passar o cursor": "Show data on hover",
    "Espessura da linha:": "Line width:",
    "Tamanho dos marcadores:": "Marker size:",
    "Máximo de pontos/séries:": "Maximum points/series:",
    # Trendline
    "Mostrar regressão linear": "Show linear trendline",
    "Traça uma regressão linear vermelha sólida usando apenas valores válidos": "Draw a solid red linear trendline using valid values only",
    "Série principal": "Primary series",
    "Todas as séries": "All series",
    "Aplicar a:": "Apply to:",
    "A trendline é calculada localmente e não substitui o VEL fornecido pelo produto.": "The trendline is calculated locally and does not replace the product VEL.",
    "Trendline — VEL {value} mm/yr": "Trendline — VEL {value} mm/yr",
    # Grid
    "Gridlines": "Gridlines",
    "Mostrar gridlines horizontais": "Show horizontal gridlines",
    "Mostrar gridlines verticais": "Show vertical gridlines",
    "Sólida": "Solid",
    "Tracejada": "Dashed",
    "Estilo horizontal:": "Horizontal style:",
    "Estilo vertical:": "Vertical style:",
    "As gridlines usam cor preta com opacidade discreta.": "Gridlines use black with restrained opacity.",
    # Shading
    "Período sombreado": "Shaded period",
    "Mostrar faixa cinza": "Show gray band",
    "Data inicial:": "Start date:",
    "Data final:": "End date:",
    "Opacidade:": "Opacity:",
    # Mean
    "Usar somente aquisições comuns a todos os pontos": "Use acquisitions common to all points only",
    "Referenciar cada série em zero antes da média": "Reference each series to zero before averaging",
    "Mostrar média ± 1 desvio-padrão": "Show mean ± 1 standard deviation",
    "Mostrar séries individuais ao fundo": "Show individual series in the background",
    "Sem o intervalo comum, a média usa os valores disponíveis em cada aquisição e exige pelo menos dois pontos. O N utilizado pode variar.": "Without the common interval, the mean uses available values at each acquisition and requires at least two points. The N used may vary.",
    # Additional properties
    "Propriedades adicionais": "Additional properties",
    "Mostrar propriedades selecionadas no painel": "Show selected properties in the panel",
    "Incluir propriedades selecionadas no cabeçalho exportado": "Include selected properties in the exported header",
    "Os campos disponíveis são lidos da camada atual. Em séries individuais é mostrado o valor da feição; em médias, a média dos campos numéricos.": "Available fields are read from the current layer. Individual series show the feature value; means show the average of numeric fields.",
    "Selecionar todos": "Select all",
    "Limpar": "Clear",
    "Nenhum campo adicional disponível na camada atual.": "No additional field is available in the current layer.",
    "Vários valores": "Multiple values",
    # Axes
    "Eixo Y": "Y axis",
    "Eixo X": "X axis",
    "Usar limites manuais": "Use manual limits",
    "Mínimo:": "Minimum:",
    "Máximo:": "Maximum:",
    "Intervalo dos ticks:": "Tick interval:",
    "Usar período manual": "Use manual period",
    "Intervalo dos ticks (dias):": "Tick interval (days):",
    # Export
    "Exportação": "Export",
    "Formato:": "Format:",
    "Largura:": "Width:",
    "Altura:": "Height:",
    "Resolução:": "Resolution:",
    "Incluir cabeçalho com os dados da série": "Include header with series data",
    "Fundo transparente": "Transparent background",
    "Incluir marca d'água do plugin na exportação": "Include plugin watermark in export",
    "Mostrar marca d'água também na visualização": "Show watermark in the viewer as well",
    "Centro": "Center",
    "Inferior direito": "Lower right",
    "Inferior esquerdo": "Lower left",
    "Superior direito": "Upper right",
    "Superior esquerdo": "Upper left",
    "Posição do logo:": "Logo position:",
    "Tamanho do logo:": "Logo size:",
    "Salvar gráfico atual...": "Save current chart...",
    "Salvar séries/médias separadamente...": "Save series/means separately...",
    "Cria um arquivo individual para cada série ou média poligonal exibida": "Create one file for each displayed series or polygon mean",
    "O cabeçalho usa os nomes literais VEL/V_STDEV da camada. PNG usa o DPI; SVG e PDF permanecem vetoriais, com o logo raster incorporado.": "The header uses the layer's literal VEL/V_STDEV field names. PNG uses DPI; SVG and PDF remain vector, with the raster logo embedded.",
    "Restaurar configurações padrão do gráfico": "Restore default chart settings",
    "As configurações são aplicadas imediatamente e armazenadas no projeto QGIS.": "Settings are applied immediately and stored in the QGIS project.",
    "Não há gráfico válido para exportar.": "There is no valid chart to export.",
    "Falha na exportação": "Export failed",
    "Exportação concluída": "Export completed",
    "Exportação em lote": "Batch export",
    "O gráfico atual não contém séries individuais exportáveis.": "The current chart does not contain exportable individual series.",
    "Falha na exportação em lote": "Batch export failed",
    "O estado atual do gráfico não contém dados exportáveis.": "The current chart state contains no exportable data.",
    # Selection and reading
    "Nenhuma feição selecionada.\nSelecione um ou mais pontos no mapa.": "No feature selected.\nSelect one or more points on the map.",
    "Use uma ferramenta normal de seleção do QGIS para escolher os pontos.": "Use a standard QGIS selection tool to choose the points.",
    "Não foi possível construir a série temporal.": "The time series could not be built.",
    "Erro desconhecido na leitura da feição.": "Unknown error while reading the feature.",
    "Nenhuma das séries selecionadas pôde ser lida.": "None of the selected series could be read.",
    "A média requer pelo menos dois pontos selecionados.": "The mean requires at least two selected points.",
    "Selecione dois ou mais pontos na mesma camada para calcular a média.": "Select two or more points in the same layer to calculate the mean.",
    "Não foi possível ler pelo menos duas séries válidas para a média.": "At least two valid series could not be read for the mean.",
    "Não foi possível calcular a média das séries.": "The series mean could not be calculated.",
    "somente aquisições comuns": "common acquisitions only",
    "séries referenciadas em zero": "series referenced to zero",
    # Plot labels and titles
    "Datas": "Dates",
    "Deslocamento (mm)": "Displacement (mm)",
    "Média": "Mean",
    "Média ± 1 desvio-padrão": "Mean ± 1 standard deviation",
    "Trendline": "Trendline",
    "séries": "series",
    "ponto": "point",
    "pontos": "points",
    "média de": "mean of",
    "{count} séries — {component}": "{count} series — {component}",
    "Média de {count} pontos — {component}": "Mean of {count} points — {component}",
    "Médias de {count} polígonos — {component}": "Means of {count} polygons — {component}",
    # Plot warnings
    "Período X manual ignorado: datas inválidas": "Manual X period ignored: invalid dates",
    "Período X manual ignorado: início posterior ao fim": "Manual X period ignored: start is later than end",
    "Limites Y manuais ignorados: mínimo deve ser menor que máximo": "Manual Y limits ignored: minimum must be lower than maximum",
    "Sombreamento ignorado: datas inválidas": "Shading ignored: invalid dates",
    "Sombreamento ignorado: início posterior ao fim": "Shading ignored: start is later than end",
    # Reader/statistics/spatial errors
    "A camada não possui campos de atributos.": "The layer has no attribute fields.",
    "A camada precisa ter pelo menos dois campos temporais válidos no formato DYYYYMMDD.": "The layer must have at least two valid time fields in DYYYYMMDD format.",
    "Nenhum campo CODE ou campo de exibição utilizável foi encontrado; o ID interno da feição será usado como rótulo.": "No CODE field or usable display field was found; the internal feature ID will be used as the label.",
    "A feição recebida é inválida.": "The supplied feature is invalid.",
    "max_features deve ser maior que zero ou None.": "max_features must be greater than zero or None.",
    "Nenhuma camada foi fornecida.": "No layer was supplied.",
    "A camada precisa ser uma QgsVectorLayer.": "The layer must be a QgsVectorLayer.",
    "A camada vetorial é inválida.": "The vector layer is invalid.",
    "A camada precisa possuir geometria de ponto.": "The layer must have point geometry.",
    "O esquema informado pertence a outra camada. Gere um novo esquema com inspect_layer(layer).": "The supplied schema belongs to another layer. Generate a new schema with inspect_layer(layer).",
    "Nenhuma série válida foi fornecida para a média.": "No valid series was supplied for the mean.",
    "As séries selecionadas não possuem datas de aquisição.": "The selected series have no acquisition dates.",
    "Não existe nenhuma aquisição válida comum a todos os pontos selecionados.": "There is no valid acquisition common to all selected points.",
    "Não foi possível calcular a média no intervalo comum selecionado.": "The mean could not be calculated over the selected common interval.",
    "Não há aquisições com pelo menos dois pontos válidos para calcular a média.": "There are no acquisitions with at least two valid points for calculating the mean.",
    "O polígono está vazio.": "The polygon is empty.",
    "A geometria fornecida não é poligonal.": "The supplied geometry is not polygonal.",
    "O polígono é inválido e o reparo não produziu uma área poligonal.": "The polygon is invalid and repair did not produce a polygonal area.",
    "O SRC de origem do polígono não é válido.": "The polygon source CRS is invalid.",
    "O SRC da camada de pontos não é válido.": "The point-layer CRS is invalid.",
    "A camada de pontos não está disponível.": "The point layer is not available.",
    "A camada de destino não é pontual.": "The target layer is not a point layer.",
    "Nenhuma feição está selecionada na camada poligonal.": "No feature is selected in the polygon layer.",
    "A camada poligonal não possui feições para processar.": "The polygon layer has no features to process.",
    "A camada pontual InSAR não está disponível.": "The InSAR point layer is not available.",
    "A camada poligonal não está disponível.": "The polygon layer is not available.",
    "Nenhum polígono foi fornecido para o cálculo.": "No polygon was supplied for the calculation.",
    "feição sem geometria poligonal válida": "feature without valid polygon geometry",
    "nenhum dos pontos contidos possui série temporal válida": "none of the contained points has a valid time series",
    "Nenhum dos polígonos processados contém pontos da camada InSAR.": "None of the processed polygons contains points from the InSAR layer.",
    "resultado vazio": "empty result",
    "{component} · {count} aquisições · {start} a {end}": "{component} · {count} acquisitions · {start} to {end}",
    "Falha inesperada: {kind}: {error}": "Unexpected failure: {kind}: {error}",
    "Falha inesperada na seleção espacial: {kind}: {error}": "Unexpected spatial-selection failure: {kind}: {error}",
    "{count} média(s) calculada(s)": "{count} mean(s) calculated",
    "{count} polígono(s) examinado(s)": "{count} polygon(s) examined",
    "{count} sem pontos": "{count} without points",
    "{count} com erro": "{count} with errors",
    "Nenhuma camada ativa no visualizador.": "No active layer in the viewer.",
    "FID {fid}: feição inválida ou removida.": "FID {fid}: invalid or removed feature.",
    "{count} arquivo(s) salvo(s) em:\n{destination}": "{count} file(s) saved to:\n{destination}",
    "\n\n{count} item(ns) falharam.": "\n\n{count} item(s) failed.",
    "Exportação em lote: {saved} arquivo(s) salvo(s){failures}": "Batch export: {saved} file(s) saved{failures}",
    "; {count} falha(s).": "; {count} failure(s).",
    "Erro desconhecido.": "Unknown error.",
    "1 selecionada": "1 selected",
    "{count} selecionadas": "{count} selected",
    "{count} valores válidos": "{count} valid values",
    "{count} ausências/999": "{count} missing/999",
    "{count} feições selecionadas": "{count} features selected",
    "{count} séries exibidas": "{count} series displayed",
    "{count} gráficos separados exibidos": "{count} separate charts displayed",
    "limite atual de {count} séries aplicado": "current limit of {count} series applied",
    "limite atual de {count} pontos aplicado": "current limit of {count} points applied",
    "{count} séries ignoradas por erro de leitura": "{count} series ignored because of read errors",
    "média calculada com {count} pontos": "mean calculated from {count} points",
    "N variável entre {minimum} e {maximum}": "variable N from {minimum} to {maximum}",
    "N = {count} por aquisição": "N = {count} per acquisition",
    "{count} média(s) poligonal(is) exibida(s)": "{count} polygon mean(s) displayed",
    "camada {name}": "layer {name}",
    "{count} participação(ões) de pontos": "{count} point participation(s)",
    "entre {minimum} e {maximum} pontos por polígono": "between {minimum} and {maximum} points per polygon",
    "{count} pontos por polígono": "{count} points per polygon",
    "{count} polígono(s) sem pontos ignorado(s)": "{count} polygon(s) without points ignored",
    "{count} polígono(s) com erro ignorado(s)": "{count} polygon(s) with errors ignored",
    "{count} médias poligonais": "{count} polygon means",
    "Média de {count} pontos": "Mean of {count} points",
    "{count} séries": "{count} series",
    "FID {fid}: erro de leitura": "FID {fid}: read error",
    "O cálculo solicitado contém {count} polígonos. O limite de segurança desta versão é {limit}; selecione um subconjunto e use 'Somente selecionados'.": "The requested calculation contains {count} polygons. This version's safety limit is {limit}; select a subset and use 'Selected only'.",
    "{count} feições selecionadas; o modo Série única exibe a feição escolhida mais recentemente": "{count} features selected; Single series mode displays the most recently selected feature",
    "área desenhada": "drawn area",
    "polígono de {layer}": "polygon from {layer}",
    "{minimum:.1f} a {maximum:.1f}{suffix}": "{minimum:.1f} to {maximum:.1f}{suffix}",
    "{start} a {end}": "{start} to {end}",
    "Salvar gráfico": "Save chart",
    "Gráfico exportado para {path}.": "Chart exported to {path}.",
    "Gráfico salvo em:\n{path}": "Chart saved to:\n{path}",
    "Escolher pasta para os gráficos": "Choose folder for charts",
    "Data: {date}": "Date: {date}",
    "Deslocamento acumulado: {value:.1f} mm": "Cumulative displacement: {value:.1f} mm",
    "A camada selecionada não é compatível.": "The selected layer is not compatible.",
    "{value:.1f} mm/ano": "{value:.1f} mm/year",
    "Imagem PNG (*.png)": "PNG image (*.png)",
    "Gráfico vetorial SVG (*.svg)": "SVG vector chart (*.svg)",
    "Documento PDF (*.pdf)": "PDF document (*.pdf)",
    "Nenhum arquivo foi salvo.\n\n{detail}": "No file was saved.\n\n{detail}",
    "Não foi possível salvar o gráfico.\n\n{kind}: {error}": "The chart could not be saved.\n\n{kind}: {error}",
    "Série": "Series",
    "A feição de ID {fid} não possui nenhuma observação temporal válida.": "Feature ID {fid} has no valid time-series observations.",
    "Sentinela inválido: {value}": "Invalid sentinel: {value}",
    "Sentinela deve ser finito: {value}": "Sentinel must be finite: {value}",
    "A feição não possui o campo esperado: {field}.": "The feature does not have the expected field: {field}.",
    "Foram encontradas datas de aquisição duplicadas: {dates}": "Duplicate acquisition dates were found: {dates}",
    "Campos parecidos com datas foram ignorados por não seguirem uma data DYYYYMMDD válida: {fields}": "Date-like fields were ignored because they do not contain a valid DYYYYMMDD date: {fields}",
    "O campo CODE não foi encontrado; o campo de exibição da camada será usado apenas como rótulo: {field}.": "The CODE field was not found; the layer display field will be used only as a label: {field}.",
    "Há nomes de campos ambíguos quando ignoramos maiúsculas e minúsculas: {fields}": "Field names are ambiguous when letter case is ignored: {fields}",
    "Não foi possível identificar a componente InSAR. Pares aceitos: {pairs}.": "The InSAR component could not be identified. Accepted pairs: {pairs}.",
    "A camada contém mais de um par de campos de componente e é ambígua: {labels}.": "The layer contains more than one component field pair and is ambiguous: {labels}.",
    "Selecione pelo menos {count} pontos para calcular a média.": "Select at least {count} points to calculate the mean.",
    "sem identificação": "unidentified",
    "A série {identifier} não possui o mesmo eixo temporal das demais.": "Series {identifier} does not have the same time axis as the others.",
    "A série {identifier} não possui observações válidas.": "Series {identifier} has no valid observations.",
    "O polígono é inválido e não pôde ser reparado: {error}": "The polygon is invalid and could not be repaired: {error}",
    "Não foi possível reprojetar o polígono para a camada de pontos: {error}": "The polygon could not be reprojected to the point layer: {error}",
    "Operação de seleção desconhecida: {operation}": "Unknown selection operation: {operation}",
    "O cálculo solicitado contém {count} polígonos. O limite de segurança desta versão é {limit}; processe somente uma seleção menor.": "The requested calculation contains {count} polygons. This version's safety limit is {limit}; process a smaller selection.",
    "Polígono FID {fid}: {count} ponto(s) ignorado(s) por erro de leitura.": "Polygon FID {fid}: {count} point(s) ignored because of read errors.",
    "Polígono FID {fid}: {error}": "Polygon FID {fid}: {error}",
    "Polígono FID {fid}: {kind}: {error}": "Polygon FID {fid}: {kind}: {error}",
    "Nenhuma média poligonal pôde ser calculada: {detail}": "No polygon mean could be calculated: {detail}",
    "Média de {count} {noun}": "Mean of {count} {noun}",
    "Formato de exportação não suportado: {format}": "Unsupported export format: {format}",
}


def normalize_locale(value: object) -> str:
    text = str(value or "").strip().replace("-", "_")
    lower = text.casefold()
    if lower.startswith("pt"):
        return _PT_BR
    return _EN


def detect_requested_locale() -> str:
    forced = os.environ.get("VST_FORCE_LOCALE", "").strip()
    if forced:
        return forced
    try:
        from qgis.PyQt.QtCore import QLocale, QSettings

        settings = QSettings()
        configured = settings.value("locale/userLocale", "")
        if configured:
            return str(configured)
        return str(QLocale.system().name())
    except Exception:
        return "en"


def initialize_locale(locale: Optional[str] = None, *, log: bool = True) -> str:
    global _requested_locale, _active_locale
    _requested_locale = str(locale or detect_requested_locale())
    _active_locale = normalize_locale(_requested_locale)
    if log:
        _log_locale()
    return _active_locale


def active_locale() -> str:
    return _active_locale


def requested_locale() -> str:
    return _requested_locale


def language_name() -> str:
    return "Português (Brasil)" if _active_locale == _PT_BR else "English"


def tr(source_pt: object, **values) -> str:
    text = str(source_pt)
    if _active_locale == _PT_BR:
        translated = text
    else:
        translated = PT_TO_EN.get(text)
        if translated is None:
            translated = _translate_dynamic_to_english(text)
    if values:
        try:
            translated = translated.format(**values)
        except (KeyError, ValueError, IndexError):
            pass
    return translated


def _translate_dynamic_to_english(text: str) -> str:
    substitutions = (
        (r"^(\d+) selecionada(?:s)?$", r"\1 selected"),
        (r"^(.*?) · (\d+) aquisições · (.*?) a (.*?)$", r"\1 · \2 acquisitions · \3 to \4"),
        (r"^(\d+) média\(s\) calculada\(s\)$", r"\1 mean(s) calculated"),
        (r"^(\d+) polígono\(s\) examinado\(s\)$", r"\1 polygon(s) examined"),
        (r"^(\d+) sem pontos$", r"\1 without points"),
        (r"^(\d+) com erro$", r"\1 with errors"),
        (r"^(\d+) feições selecionadas$", r"\1 features selected"),
        (r"^(\d+) séries exibidas$", r"\1 series displayed"),
        (r"^(\d+) gráficos separados exibidos$", r"\1 separate charts displayed"),
        (r"^limite atual de (\d+) séries aplicado$", r"current limit of \1 series applied"),
        (r"^limite atual de (\d+) pontos aplicado$", r"current limit of \1 points applied"),
        (r"^(\d+) séries ignoradas por erro de leitura$", r"\1 series ignored because of read errors"),
        (r"^média calculada com (\d+) pontos$", r"mean calculated from \1 points"),
        (r"^N variável entre (\d+) e (\d+)$", r"variable N from \1 to \2"),
        (r"^N = (\d+) por aquisição$", r"N = \1 per acquisition"),
        (r"^(\d+) médias poligonais$", r"\1 polygon means"),
        (r"^(\d+) média\(s\) poligonal\(is\) exibida\(s\)$", r"\1 polygon mean(s) displayed"),
        (r"^camada (.+)$", r"layer \1"),
        (r"^(\d+) participação\(ões\) de pontos$", r"\1 point participation(s)"),
        (r"^entre (\d+) e (\d+) pontos por polígono$", r"between \1 and \2 points per polygon"),
        (r"^(\d+) pontos por polígono$", r"\1 points per polygon"),
        (r"^(\d+) polígono\(s\) sem pontos ignorado\(s\)$", r"\1 polygon(s) without points ignored"),
        (r"^(\d+) polígono\(s\) com erro ignorado\(s\)$", r"\1 polygon(s) with errors ignored"),
        (r"^Média de (\d+) pontos$", r"Mean of \1 points"),
        (r"^(\d+) séries$", r"\1 series"),
        (r"^(\d+) valores válidos$", r"\1 valid values"),
        (r"^(\d+) ausências/999$", r"\1 missing/999"),
        (r"^Data: (.+)$", r"Date: \1"),
        (r"^Deslocamento acumulado: (.+)$", r"Cumulative displacement: \1"),
        (r"^N: (\d+) ponto$", r"N: \1 point"),
        (r"^N: (\d+) pontos$", r"N: \1 points"),
        (r"^(\d{2}/\d{2}/\d{4}) a (\d{2}/\d{2}/\d{4})(.*)$", r"\1 to \2\3"),
        (r"^(.+) mm/ano$", r"\1 mm/year"),
        (r"^Gráfico exportado para (.+)\.$", r"Chart exported to \1."),
        (r"^Exportação em lote: (\d+) arquivo\(s\) salvo\(s\)(.*)$", r"Batch export: \1 file(s) saved\2"),
    )
    for pattern, replacement in substitutions:
        match = re.match(pattern, text)
        if match:
            return re.sub(pattern, replacement, text) if isinstance(replacement, str) else replacement(match)
    return text


def translate_widget_tree(root) -> None:
    """Translate static text already assigned to a Qt widget tree."""
    if _active_locale == _PT_BR:
        return

    try:
        from qgis.PyQt.QtWidgets import (
            QAbstractButton,
            QComboBox,
            QGroupBox,
            QLabel,
            QWidget,
        )
    except ImportError:
        return

    if not isinstance(root, QWidget):
        return

    widgets = [root, *root.findChildren(QWidget)]

    for widget in widgets:
        title = widget.windowTitle()
        if title in PT_TO_EN:
            widget.setWindowTitle(tr(title))

        tip = widget.toolTip()
        if tip in PT_TO_EN:
            widget.setToolTip(tr(tip))

        if isinstance(widget, QGroupBox):
            title = widget.title()
            if title in PT_TO_EN:
                widget.setTitle(tr(title))

        if isinstance(widget, (QLabel, QAbstractButton)):
            text = widget.text()
            if text in PT_TO_EN:
                widget.setText(tr(text))

        if isinstance(widget, QComboBox):
            for index in range(widget.count()):
                text = widget.itemText(index)
                if text in PT_TO_EN:
                    widget.setItemText(index, tr(text))


def _log_locale() -> None:
    message = (
        "Time Series Viewer: requested locale="
        f"{_requested_locale}, loaded language={_active_locale}"
    )

    try:
        from qgis.core import Qgis, QgsMessageLog
    except ImportError:
        return

    QgsMessageLog.logMessage(
        message,
        "Time Series Viewer",
        Qgis.Info,
    )


# Safe module default. plugin.py calls initialize_locale again during startup.
initialize_locale(log=False)
