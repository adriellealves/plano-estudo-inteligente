# Passo a passo para adicionar upload, leitura, anotações e salvamento de PDFs por disciplina

## 1. Backend (Python/Flask)
### a) Instalar dependências
- Instalar Python (recomendado: versão 3.10+)
- Instalar Flask: `pip install flask flask-cors`
- Instalar PyPDF2 (manipulação básica de PDFs): `pip install PyPDF2`
- (Opcional) Instalar pdf-annotate para manipular anotações: `pip install pdf-annotate`

### b) Criar rotas para PDF
- Rota para upload de PDF, salvando em pasta por disciplina
- Rota para listar PDFs por disciplina
- Rota para baixar/visualizar PDF
- (Opcional) Rota para salvar anotações feitas no PDF

## 2. Frontend (React/Vite)
### a) Instalar dependências
- Instalar Node.js (recomendado: versão 18+)
- Instalar dependências do projeto: `npm install`
- Instalar pdf.js para visualização: `npm install pdfjs-dist`
- Instalar react-pdf-highlighter para anotações: `npm install react-pdf-highlighter`

### b) Criar componentes
- Componente de upload de PDF (seleciona disciplina e arquivo)
- Componente de listagem de PDFs por disciplina
- Componente de visualização de PDF com anotações (destaques, círculos, comentários)
- Botão para salvar/exportar PDF anotado

## 3. Integração
- Conectar frontend e backend via API (fetch/axios)
- Enviar PDFs e anotações para o backend
- Permitir download/visualização dos PDFs anotados

## 4. Extras/Sugestões
- Permitir busca por conteúdo nos PDFs
- Dashboard de progresso por disciplina
- Notificações de novos materiais

## 5. Referências
- Flask: https://flask.palletsprojects.com/
- PyPDF2: https://pypdf2.readthedocs.io/
- pdf.js: https://mozilla.github.io/pdf.js/
- react-pdf-highlighter: https://github.com/agentcooper/react-pdf-highlighter

---
Esse roteiro cobre desde a instalação até a integração das funcionalidades de PDF. Se quiser detalhar algum passo, só pedir!
