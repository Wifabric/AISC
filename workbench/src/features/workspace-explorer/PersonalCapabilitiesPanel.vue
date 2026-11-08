<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useRuntimeStore } from "../../stores/runtime";
import { usePersonalCapabilitiesStore } from "../../stores/personalCapabilities";
const runtime = useRuntimeStore();
const store = usePersonalCapabilitiesStore();
const { templates, profiles, draft, error, notice, loading, busy, loaded, historical, dirty, selected, oldRevision } = storeToRefs(store);
const { latest, load, edit, create, discard, restore, save, openAgent } = store;
</script>

<template>
  <section class="personal-capabilities" data-testid="personal-capabilities">
    <h2>个人能力</h2>
    <p>从模板建立自己的规则和技能，通过反馈持续修订。保存在当前工作区，启用后随新建的 Claude / Codex 会话注入。</p>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
    <p v-if="notice" role="status" class="success">{{ notice }}</p>
    <p v-if="!runtime.workspace">请先打开工作区。</p>
    <template v-else>
      <div class="actions">
        <button class="ui-button sm" :disabled="loading || busy" @click="load">刷新</button>
        <button class="ui-button sm" :disabled="!loaded || busy || dirty" @click="create()">新建空白能力</button>
      </div>
      <p v-if="loading" role="status">正在读取个人能力…</p>
      <h3>模板市场 · 初始模板</h3>
      <div class="cards">
        <article v-for="template in templates" :key="template.id" class="card">
          <strong>{{ template.name }}</strong><p>{{ template.description }}</p>
          <details><summary>查看模板内容</summary><pre>{{ template.rules }}

{{ template.skill }}</pre></details>
          <button class="ui-button sm" :disabled="busy || dirty" :data-testid="'personal-template-' + template.id" @click="create(template)">创建个人副本</button>
        </article>
      </div>
      <h3>我的能力</h3>
      <p v-if="loaded && !profiles.length">尚无个人能力。选择上方模板，修改后保存；模板本身不会被改动。</p>
      <nav class="cards" aria-label="我的能力">
        <button v-for="profile in profiles" :key="profile.id" class="card choice" :aria-pressed="draft?.id === profile.id"
          :disabled="busy || dirty" @click="edit(profile)">
          {{ latest(profile).name }} · 第 {{ latest(profile).revision }} 版 · {{ latest(profile).enabled ? '新会话启用' : '已停用' }}
        </button>
      </nav>
      <form v-if="draft" class="card editor" data-testid="personal-editor" @submit.prevent="save">
        <p v-if="dirty" role="status">有未保存修改。保存或放弃后可切换能力。</p>
        <fieldset :disabled="busy">
          <label>名称<input v-model="draft.name" maxlength="120" required data-testid="personal-name" /></label>
          <label>个人规则<textarea v-model="draft.rules" rows="4" maxlength="4000" data-testid="personal-rules" /></label>
          <label>个人技能（可粘贴自己的 SKILL.md 内容）<textarea v-model="draft.skill" rows="8" maxlength="8000" required data-testid="personal-skill" /></label>
          <label>本次反馈 / 修改原因<textarea v-model="draft.reason" rows="2" maxlength="2000" required data-testid="personal-reason" /></label>
          <label>验证结果<input v-model="draft.verification" maxlength="2000" required placeholder="例如：待验证；已在某项任务中验证，结果为…" data-testid="personal-verification" /></label>
          <label class="toggle"><input v-model="draft.enabled" type="checkbox" data-testid="personal-enabled" />在当前工作区的新会话中启用</label>
        </fieldset>
        <p>保存会增加一个版本，历史内容保留。停用也需要保存。已有会话保留启动时的快照，其他工作区不受影响；平台不会执行文本中的脚本或覆盖全局配置。</p>
        <div class="actions">
          <button class="ui-button" type="submit" :disabled="busy || !loaded || !dirty" data-testid="personal-save">保存新版本</button>
          <button class="ui-button sm" type="button" :disabled="busy" @click="discard">放弃未保存修改</button>
        </div>
        <div v-if="selected" class="history">
          <label>修订历史<select v-model.number="historical" data-testid="personal-history"><option :value="0">选择版本查看</option><option v-for="revision in [...selected.history].reverse()" :key="revision.revision" :value="revision.revision">第 {{ revision.revision }} 版 · {{ revision.created_at }}</option></select></label>
          <article v-if="oldRevision">
            <p>修改原因：{{ oldRevision.reason }}</p><p>验证结果：{{ oldRevision.verification }}</p>
            <pre>{{ oldRevision.rules }}

{{ oldRevision.skill }}</pre>
            <button type="button" class="ui-button sm" :disabled="busy" @click="restore(oldRevision)">将此版本恢复到草稿</button>
          </article>
        </div>
        <div v-if="selected && latest(selected).enabled" class="actions">
          <button type="button" class="ui-button sm" :disabled="busy || dirty" @click="openAgent('claude')">用 Claude 验证</button>
          <button type="button" class="ui-button sm" :disabled="busy || dirty" @click="openAgent('codex')">用 Codex 验证</button>
        </div>
      </form>
      <p>需要持续记录任务、对话和实践成果时，使用下方主题工作坊。个人能力会与所选主题一起注入，也可独立用于普通对话。</p>
    </template>
  </section>
</template>

<style scoped>
.personal-capabilities { display: grid; gap: var(--space-2); }
h2, h3, p { margin: 0; }
p, label, pre { font-size: var(--font-xs); line-height: 1.6; overflow-wrap: anywhere; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)); gap: var(--space-2); }
.card { display: grid; gap: var(--space-2); padding: var(--space-3); border: var(--border-w) solid var(--border-2); border-radius: var(--radius-sm); background: var(--surface); color: var(--text); }
.choice { text-align: left; cursor: pointer; }
.choice[aria-pressed="true"] { border-color: var(--accent); }
.actions { display: flex; flex-wrap: wrap; gap: var(--space-2); }
fieldset { display: grid; gap: var(--space-2); border: 0; padding: 0; margin: 0; min-width: 0; }
label { display: grid; gap: var(--space-1); }
input, textarea, select { box-sizing: border-box; width: 100%; min-width: 0; font: inherit; color: var(--text); background: var(--surface-2); border: var(--border-w) solid var(--border); border-radius: var(--radius-sm); padding: var(--space-2); }
textarea { resize: vertical; }
.toggle { display: flex; align-items: center; }
.toggle input { width: auto; }
pre { white-space: pre-wrap; }
.error { color: var(--error); }
.success { color: var(--accent); }
.history { display: grid; gap: var(--space-2); }
</style>
