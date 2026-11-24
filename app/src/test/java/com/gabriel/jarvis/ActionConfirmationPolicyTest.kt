package com.gabriel.jarvis

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ActionConfirmationPolicyTest {
    @Test
    fun modelProposalsWithSideEffectsRequireConfirmation() {
        val actions = listOf(
            "abrir_app",
            "pesquisar",
            "ler_tela",
            "mensagem",
            "digitar",
            "criar_projeto",
            "auditar_projeto"
        )
        actions.forEach { action ->
            assertTrue("$action must require confirmation when proposed by the model",
                Acoes.requerConfirmacao(action, origemModelo = true))
        }
    }

    @Test
    fun onlyLowRiskReadOnlyModelActionsCanSkipConfirmation() {
        val safeActions = listOf(
            "bateria",
            "hora",
            "data",
            "calcular",
            "status_codigo",
            "security_lab",
            "money_lab"
        )
        safeActions.forEach { action ->
            assertFalse("$action is a read-only action",
                Acoes.requerConfirmacao(action, origemModelo = true))
        }
    }

    @Test
    fun destructiveAndScreenControlActionsAlwaysRequireConfirmation() {
        val sensitiveActions = listOf(
            "tocar",
            "digitar",
            "esquecer",
            "apagar_anotacoes",
            "organizar_downloads",
            "desfazer_organizacao"
        )
        sensitiveActions.forEach { action ->
            assertTrue("$action must require confirmation even for a direct voice command",
                Acoes.requerConfirmacao(action, origemModelo = false))
        }
    }

    @Test
    fun explicitLowRiskVoiceCommandsRemainImmediate() {
        assertFalse(Acoes.requerConfirmacao("abrir_app", origemModelo = false))
        assertFalse(Acoes.requerConfirmacao("pesquisar", origemModelo = false))
        assertFalse(Acoes.requerConfirmacao("bateria", origemModelo = false))
    }
}
