"""
TP1 - BCC327 - Leitura dos modelos CCO (.vtk) e estatísticas.

Da biblioteca (PyVista/VTK): ler o arquivo.
Do grupo: contagem de segmentos, detecção do atributo de raio, estatísticas
e o raio auxiliar usado para a espessura dos tubos.
"""
import numpy as np
import pyvista as pv

# nomes que costumam aparecer para o atributo de raio nos arquivos
NOMES_RAIO = ("raio", "radius", "radii", "raios", "r", "vessel_radius")


def carregar_modelo(caminho):
    """Lê o VTK e garante que o resultado seja um PolyData com linhas."""
    malha = pv.read(caminho)
    if not isinstance(malha, pv.PolyData):
        # UnstructuredGrid com células de linha -> PolyData (mantém as linhas)
        malha = malha.extract_geometry()
    return malha


def extrair_segmentos(malha):
    """Pares de índices de pontos, um por segmento de reta.
    Uma célula 'line' pode ser uma polilinha de n pontos (n-1 segmentos)."""
    arr, i, segs = malha.lines, 0, []
    while i < len(arr):
        n = int(arr[i])
        idx = arr[i + 1:i + 1 + n]
        segs += [(idx[k], idx[k + 1]) for k in range(n - 1)]
        i += n + 1
    return np.array(segs, dtype=int)


def contar_segmentos(malha):
    return len(extrair_segmentos(malha))


def achar_raio(malha):
    """Procura o array de raio em cell_data e point_data.
    Retorna (nome, 'cell' | 'point') ou (None, None)."""
    for onde, dados in (("cell", malha.cell_data), ("point", malha.point_data)):
        for nome in dados.keys():
            if nome.lower() in NOMES_RAIO:
                return nome, onde
    for onde, dados in (("cell", malha.cell_data), ("point", malha.point_data)):
        for nome in dados.keys():
            if "rad" in nome.lower() or "raio" in nome.lower():
                return nome, onde
    return None, None


def estatisticas(malha, nome_raio, onde):
    dados = malha.cell_data if onde == "cell" else malha.point_data
    r = np.asarray(dados[nome_raio])
    return {
        "pontos": malha.n_points,
        "segmentos": contar_segmentos(malha),
        "r_min": float(r.min()),
        "r_max": float(r.max()),
        "plano": abs(malha.bounds[5] - malha.bounds[4]) < 1e-12,
    }


def imprimir_info(malha, nome_raio, onde):
    print("=" * 50)
    print(f"Pontos:     {malha.n_points}")
    print(f"Segmentos:  {contar_segmentos(malha)}")
    b = malha.bounds
    print(f"Bounds:     x[{b[0]:.4g}, {b[1]:.4g}]  y[{b[2]:.4g}, {b[3]:.4g}]  "
          f"z[{b[4]:.4g}, {b[5]:.4g}]")
    print(f"Arrays em point_data: {list(malha.point_data.keys())}")
    print(f"Arrays em cell_data:  {list(malha.cell_data.keys())}")
    if nome_raio is None:
        print("!! Não achei o atributo de raio. Veja os arrays acima e use --campo-raio.")
    else:
        e = estatisticas(malha, nome_raio, onde)
        print(f"Raio ('{nome_raio}' em {onde}_data): "
              f"min = {e['r_min']:.6g}   max = {e['r_max']:.6g}")
    print("=" * 50)


def preparar_raio(malha, nome_raio, onde, escala):
    """Cria 'raio_vis' em point_data (necessário para gerar tubos),
    multiplicado por 'escala' só para visualização. Se o raio vier por
    célula, também cria uma versão por ponto (nome_raio + '_pt')."""
    if onde == "cell":
        pontos = malha.cell_data_to_point_data()
        malha.point_data[nome_raio + "_pt"] = pontos.point_data[nome_raio]
        base = malha.point_data[nome_raio + "_pt"]
    else:
        base = malha.point_data[nome_raio]
    malha.point_data["raio_vis"] = np.asarray(base) * escala
    return malha