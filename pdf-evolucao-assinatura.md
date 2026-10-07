# Fluxo completo de geração do PDF de evolução e assinatura digital

## 1. Objetivo

Este documento descreve todo o fluxo de geração do PDF de evolução, incluindo:

- cabeçalho do relatório;
- dados do paciente;
- dados do profissional/usuário responsável;
- corpo com os parágrafos da evolução;
- footer do relatório;
- processo de assinatura digital do PDF final;
- persistência do arquivo assinado no modelo de relatório.

Ele foi escrito para servir como referência futura para outros modelos do sistema (prescrição, diagnóstico, Adep, etc.), mantendo a mesma estrutura de montagem do relatório.

---

## 2. Arquitetura do processo

Os componentes principais envolvidos no fluxo são:

1. `prontuarios.models.Evolucao`
   - model principal que guarda a evolução.
   - contém o texto principal, tipo de evolução, atendimento, estabelecimento e usuário.

2. `prontuarios.relatorios.gerar_pdf_prontuario()`
   - responsável por construir o PDF em buffer.
   - monta o cabeçalho, dados de paciente/profissional, corpo e rodapé.

3. `admin_relatorios/*.py`
   - módulo de geração de blocos fixos do relatório.
   - contém funções de cabeçalho, dados pessoais, dados do usuário, dados do objeto, parágrafos, assinatura e rodapé.

4. `admin_relatorios.utils.assinar_pdf()`
   - recebe o PDF em bytes e o certificado PFX.
   - cria a assinatura digital CMS/PKCS7 no PDF com `endesive`.
   - insere a assinatura visual no relatório e embute o certificado no arquivo final.

5. `prontuarios.utils.salvar_pdf_prontuario()`
   - encapsula o fluxo final de persistência.
   - chama `gerar_pdf_prontuario`, assina se necessário e salva o PDF em `Relatorio`.

6. `admin_relatorios.models.Relatorio`
   - model que guarda o arquivo final em `FileField`.

---

## 3. Estrutura do fluxo de geração do PDF

### 3.1 Entrada inicial

A geração começa a partir de um objeto de evolução, por exemplo:

- `obj` = instância de `Evolucao`;
- `user` = usuário que registra a evolução;
- `assinar` = flag que habilita assinatura digital;
- `assinatura_texto` = texto que aparecerá no bloco visual da assinatura.

O método principal é:

```python
buffer = gerar_pdf_prontuario(obj, user, assinar=..., assinatura_texto=...)
```

### 3.2 A geração do PDF em buffer

A função `gerar_pdf_prontuario()` cria um `BytesIO()` e usa `reportlab.canvas.Canvas` para desenhar o documento.

O processo funciona em duas partes:

1. montagen do cabeçalho e blocos fixos;
2. fluxo do conteúdo principal (parágrafos) com quebra automática por página.

---

## 4. Cabeçalho, dados do paciente, dados do profissional e footer

A parte visual do relatório é montada por blocos separados:

### 4.1 Cabeçalho

Arquivo:

- `admin_relatorios/rel_header.py`

Função/uso:

- `genHeaderRel(logo_path, header_data, right_data, width, height)`

Responsabilidade:

- renderiza o cabeçalho do relatório;
- pode exibir logomarca, nome do estabelecimento, texto do lado direito e demais informações gerais.

### 4.2 Dados do paciente

Arquivo:

- `admin_relatorios/rel_dados_pessoais.py`

Função/uso:

- `genDadosPessoaisRel(nome_pessoa, width, height)`

Responsabilidade:

- imprime o nome do paciente;
- inclui dados pessoais do atendimento;
- normalmente fica no topo do corpo do relatório.

### 4.3 Dados do profissional/usuário

Arquivo:

- `admin_relatorios/rel_usuario.py`

Função/uso:

- `genDadosUsuarioRel(dados, width, height)`

Responsabilidade:

- mostra nome/profissional do usuário que registrou a evolução;
- exibe data e sistema de registro.

### 4.4 Dados do objeto/documento

Arquivo:

- `admin_relatorios/rel_dados_obj.py`

Função/uso:

- `genDadosObjRel(vardinpk, width, height)`

Responsabilidade:

- exibe identificadores do documento (ID, tipo etc.).

### 4.5 Footer

Arquivo:

- `admin_relatorios/rel_footer.py`

Função/uso:

- `genFooterRel(footer_data, width, height)`

Responsabilidade:

- imprime rodapé do relatório;
- normalmente inclui texto institucional ou mensagem de gerenciamento do relatório.

---

## 5. Fluxo do corpo do relatório: parágrafos e quebra de página

Arquivo:

- `admin_relatorios/rel_paragrafos.py`

A função de montagem principal no PDF final é:

```python
body_flowable = genParagrafosRel(texto_parag, content_width, 0, None, tipo=nome_modelo)
```

### 5.1 Objetivo

A lógica de corpo do relatório precisa:

- receber o texto bruto da evolução;
- limpar o HTML para texto puro;
- segmentar em blocos legíveis;
- quebrar automaticamente em páginas quando ultrapassar as dimensões do PDF;
- manter cabeçalho e footer fixos em todas as páginas.

### 5.2 Parâmetros relevantes

No `gerar_pdf_prontuario()` há o cálculo do espaço útil do corpo, como:

```python
left_margin = 12 * mm
right_margin = 12 * mm
top_margin = 10 * mm
bottom_margin = 18 * mm
content_width = page_width - left_margin - right_margin
```

E também:

```python
fixed_block_height = 54 * mm
footer_height = 12 * mm if footer_data else 0
body_top = page_height - top_margin - fixed_block_height - 8 * mm
body_bottom = bottom_margin + footer_height + 6 * mm
```

Esses valores garantem que o corpo do texto seja sempre limitado aos espaços disponíveis dentro da página.

### 5.3 Regras da quebra de páginas

Logo após o bloco fixo, o corpo é iterado:

```python
current_y = body_top
for flowable in story:
    ...
    if current_y - flowable_h < body_bottom:
        canvas_obj.showPage()
        draw_fixed_sections()
        current_y = body_top
```

Isso indica que:

- o conteúdo percorre a página até atingir o limite inferior;
- ao estourar o limite, a página é trocada;
- o cabeçalho e o footer são redesenhados na nova página;
- o conteúdo segue no restante da página nova.

### 5.4 Importante para o futuro

A quebra de páginas não deve mexer na assinatura digital do PDF final. O conteúdo do corpo pode continuar sendo fragmentado, mas a assinatura deve ser aplicada no documento final completo, depois de tudo renderizado.

---

## 6. Processo de assinatura digital

Arquivo principal:

- `admin_relatorios/utils.py`

Função principal:

```python
assinar_pdf(contasena, certificado, pdf_buffer, posicao)
```

### 6.1 Entrada

A função recebe:

- `contasena`: senha do PFX;
- `certificado`: bytes do arquivo `.pfx`;
- `pdf_buffer`: buffer em memória do PDF já gerado;
- `posicao`: posição da caixa de assinatura visual na página.

### 6.2 Carregamento do certificado

O código usa:

```python
p12 = pkcs12.load_key_and_certificates(
    certificado_data, senha, default_backend()
)
```

O retorno é tipicamente:

- `p12[0]` = chave privada;
- `p12[1]` = certificado X.509;
- `p12[2]` = cadeia opcional de certificados.

### 6.3 Dados do certificado usado na assinatura

A função lê:

- nome do assinante (`COMMON_NAME`);
- email (`SubjectAlternativeName`);
- emissor;
- validade;
- número de série;
- texto para aparecer no bloco visual.

A lógica do texto de assinatura pode ser montada assim:

```python
texto_assinatura = (
    f"{nome_assinante}\n"
    f"Assinatura Digital - ICP-Brasil\n"
    f"Emissor: {emissor}\n"
    f"Validade: {validade}\n"
    f"Nº Série: {serial}\n"
    f"{data_assinatura}"
)
```

### 6.4 Configuração do `dct` do endesive

O `dct` é o dicionário com os parâmetros usados pela assinatura digital. Ele inclui:

```python
dct = {
    "aligned": 0,
    "sigflags": 3,
    "sigflagsft": 132,
    "sigpage": sigpage,
    "sigbutton": True,
    "sigfield": "Signature1",
    "auto_sigfield": True,
    "signaturebox": (...),
    "signature": texto_assinatura,
    "contact": contact,
    "location": "Brazil",
    "signingdate": date,
    "reason": "Assinado Digitalmente",
    "password": contasena,
}
```

Esses valores fazem duas coisas:

1. inserem a assinatura visual no PDF;
2. fazem com que o `endesive` gere o CMS da assinatura no documento final.

### 6.5 Chamada crítica ao endesive

A chamada correta é:

```python
pdf_assinado = endesive_cms.sign(
    datau,
    dct,
    p12[0],
    p12[1],
    p12[2],
    "sha256",
)
```

Esse retorno é o PDF final assinado em bytes, com a assinatura CMS embutida. O mais importante é que este retorno é o que deve ser salvo em disco.

### 6.6 Verificação da assinatura embutida

Para confirmar que a assinatura existe dentro do PDF, a aplicação deve verificar:

- `/ByteRange`
- `/Contents`
- `Signature1`

Se qualquer um destes não estiver presente, o PDF não foi assinado digitalmente no formato esperado.

A lógica pode ser simplificada, por exemplo:

```python
if not (b'/ByteRange' in pdf_assinado and b'/Contents' in pdf_assinado and b'Signature1' in pdf_assinado):
    raise ValueError('PDF assinado não contém a assinatura CMS embutida do certificado digital.')
```

### 6.7 Export do certificado dentro do PDF

O `endesive` faz isso ao montar o CMS com:

- chave privada;
- certificado X.509 do PFX;
- cadeia de certificados (quando houver);
- dados do documento assinado.

O PDF final precisa conter esse payload, e a cadeia/certificado precisam estar embutidos para que o documento possa ser validado como documento assinado digitalmente.

---

## 7. Processo de persistência do PDF

Arquivo:

- `prontuarios/utils.py`

Função principal:

```python
salvar_pdf_prontuario(user, obj, assinar=False)
```

### 7.1 Fluxo do salvamento

1. lê o certifcado do usuário (`Perfil.certificado_digital`);
2. lê a senha (`Perfil.senha_certificado`);
3. chama `gerar_pdf_prontuario()`;
4. se `assinar` for verdadeiro, chama `assinar_pdf()`;
5. salva o PDF resultante no `Relatorio`; 
6. nomeia o arquivo como:
   - `modelo_dig_<id>.pdf` quando assinado;
   - `modelo_imp_<id>.pdf` quando não assinado.

### 7.2 Importante

O PDF persistido deve ser o retorno do `assinar_pdf()`, ou seja, o PDF assinado final.

Não deve ser salvo:

- o `buffer` original;
- o PDF renderizado antes da assinatura;
- apenas o texto visual do relatório.

O arquivo salvo precisa conter a assinatura real no corpo do PDF.

---

## 8. Relação entre parágrafos e assinatura

Este é ponto crucial para evitar regressões futuras:

- a geração do PDF em várias páginas não deve alterar o fluxo de assinatura digital;
- a paginação pode quebrar o conteúdo em várias páginas, mas a assinatura precisa ser aplicada ao documento completo final;
- a assinatura deve acontecer depois que todo o relatório foi montado em bytes.

Em outras palavras:

- primeiro: renderizar o documento inteiro em memória;
- depois: assinar o PDF final em bytes;
- depois: salvar o PDF assinado final.

Se a assinatura for feita antes do corpo estar completamente montado, o PDF pode ficar sem a assinatura correta ou com dados do certificado ausentes no arquivo final.

---

## 9. Checklist de validação do processo

Sempre que um novo modelo usar esse fluxo, verificar:

- [ ] o PDF em bytes foi gerado com o conteúdo completo;
- [ ] a assinatura foi aplicada ao final do PDF;
- [ ] o retorno do `endesive` foi salvo e não o buffer original;
- [ ] `Signature1` existe no PDF final;
- [ ] `/ByteRange` e `/Contents` existem no PDF final;
- [ ] o certificado foi incorporado ao CMS do PDF final;
- [ ] o PDF final salva no `Relatorio` é o assinado e não o não assinado;
- [ ] o texto visual da assinatura está visível no PDF para leitura humana;
- [ ] o PDF final pode ser validado por ferramenta de assinatura digital/ICP-Brasil.

---

## 10. Observações importantes para outros modelos

Os demais modelos do sistema devem seguir a mesma arquitetura:

- `gerar_pdf_prontuario()` ou equivalente por modelo;
- `assinar_pdf()` centralizado;
- `salvar_pdf_prontuario()` para persistência;
- `Relatorio` como armazenamento final.

A lógica de cabeçalho, paciente, profissional, rodapé e parágrafos pode variar por modelo, mas a assinatura final deve continuar obedecendo ao mesmo contrato:

- `buffer → bytes finais → assinar → salvar assinado`

---

## 11. Diagnóstico rápido de falha de assinatura

Se o PDF não estiver embutindo o certificado, os pontos a verificar são:

1. o `pdf_buffer` está correto antes da assinatura;
2. o `endesive` está recebendo `p12[0]`, `p12[1]`, `p12[2]` corretos;
3. o retorno do `endesive` está sendo salvo;
4. o PDF final contém `Signature1`, `/ByteRange` e `/Contents`;
5. a cadeia/certificado do PFX não está vazia;
6. o `pdf_buffer` não foi sobrescrito antes da assinatura final.

---

## 12. Conclusão

O fluxo funcional de geração de PDF e assinatura digital é:

1. gerar relatório em buffer;
2. montar cabeçalho, dados do paciente, dados do profissional, corpo e rodapé;
3. quebrar o conteúdo em páginas conforme necessário;
4. converter o relatório para bytes finais;
5. assinar o PDF final com `endesive`;
6. salvar o PDF assinado final no `Relatorio`;
7. manter o texto visual e a assinatura real como partes separadas, mas consistentes.

A assinatura real não pode ser confundida com o texto visual do relatório, e o PDF final salvo precisa ser o PDF assinado com o certificado embutido para valer como documento digitalmente assinado.
