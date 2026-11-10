# CCO-tree
.

2. Módulo 1: leitura e visualização (base de tudo)
3. Módulo 2: transformações e câmera
4. Módulos 3 e 4: Bresenham e Scanline (didáticos, mais fáceis de isolar)
5. Módulo 6 e 7: recortes (a parte mais pesada, 20% da nota)
6. Módulo 5: antialiasing (rápido, dá para fazer em paralelo)
7. Relatório, slides e README (não deixem para o último dia, o LaTeX toma tempo)

Checklist por módulo

Módulo 1: Leitura, primitivas e atributos

 Carregar pelo menos um .vtk
 Mostrar nº de pontos e nº de segmentos
 Mostrar raio mínimo e máximo
 Desenhar com linhas, tubos/cilindros ou ambos
 Cor e/ou espessura em função do raio
 Justificar o modelo de cor (RGB, mapa contínuo etc.) no relatório

Módulo 2: Transformações e observador

 Translação, rotação e escala
 Pelo menos 3 vistas diferentes do observador
 Projeção ortográfica vs perspectiva (se usarem 3D)
 Texto no relatório: diferença entre espaço do mundo e sistema de coordenadas da câmera

Módulo 3: Rasterização de linhas (implementação própria obrigatória)

 Bresenham (ou DDA com justificativa)
 Exemplo numérico ou visual mostrando os pixels gerados

Módulo 4: Rasterização de polígonos

 Scanline Fill em pelo menos um polígono (não precisa converter a árvore)

Módulo 5: Aliasing e antialiasing

 Comparação visual com e sem AA (supersampling, MSAA ou equivalente)
 Mostrar o efeito em linhas inclinadas ou contornos
 Explicar a técnica no relatório

Módulo 6: Recorte de segmentos

 Cohen–Sutherland (obrigatório, implementação própria)
 Um entre Liang–Barsky ou Cyrus–Beck (implementação própria)
 Discussão curta do terceiro, destacando a diferença principal
 Imagens antes e depois do recorte, sobre segmentos da árvore ou cena de teste relacionada

Módulo 7: Recorte de polígonos

 Sutherland–Hodgman num polígono de teste
 Texto explicando quando Weiler–Atherton é mais adequado (côncavos, múltiplas regiões, interseções complexas)
 Weiler–Atherton completo é diferencial, não obrigatório
Interação sugerida

Teclas para alternar vistas e projeções, mouse para rotacionar e dar zoom, tecla de liga/desliga do AA, seleção do algoritmo de recorte, exibição da janela de recorte e alternância entre cor e espessura. Não é obrigatório, mas facilita muito a demonstração.

Entregáveis (não esquecer nenhum)
 Código-fonte documentado
 Relatório em PDF + .tex (a partir do template_artigo_portugues), com figuras
 Apresentação em PDF + .tex (Beamer, template template_apresentacao_beamer_CCO), com figuras
 README com: nomes do grupo, tecnologia, dependências com versões, instalação, comando de execução, onde ficam os VTK, comandos de teclado/mouse, roteiro mínimo de teste, e o que foi feito por vocês vs. o que veio de biblioteca
 Vídeo/GIF de demonstração (opcional)
 Apresentação oral de 10 a 15 min com demo
 Tudo num .zip seguindo a estrutura Grupo_XX/, sem venv, caches ou arquivos temporários


python src/visualizador.py data\dados_modelos2D\tree2D_Nterm008.vtk --modo tubos

python src/visualizador.py data\dados_modelos3D\tree3D_Nterm016.vtk --modo tubos


Resumo do Módulo 1

O que foi feito
Um script em Python (src/visualizador.py) que carrega um modelo CCO em .vtk, imprime as estatísticas do modelo e mostra a árvore em uma janela interativa. Foi testado em dois modelos: tree2D_Nterm008.vtk (plano, z = 0) e tree3D_Nterm016.vtk (3D de verdade).

Resumo do Módulo 2

O que cada arquivo faz

transformacoes.py tem só numpy, sem PyVista. Ele monta as matrizes 4x4 de translação, escala e rotação (x, y, z), a matriz de vista (olhar_para, o equivalente do gluLookAt) e as projeções ortográfica e perspectiva. Isso é código nosso, o que é o que o professor quer ver.

modulo2_camera.py é o visualizador. Ele aplica as nossas matrizes ao modelo e posiciona a câmera, e o PyVista só desenha o resultado. Ele importa as funções do seu visualizador.py (ou do modulo1_visualizador.py, se esse for o nome).
