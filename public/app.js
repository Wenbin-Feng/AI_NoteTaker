class MarginApp {
  constructor() {
    this.notes = [];
    this.current = null;
    this.queue = Promise.resolve();
    this.timer = null;
    this.translation = null;
    this.toastTimer = null;
    this.$ = id => document.getElementById(id);
    this.bind();
    this.load();
  }

  bind() {
    this.$('newNoteBtn').addEventListener('click', () => this.newNote());
    this.$('welcomeNewBtn').addEventListener('click', () => this.newNote());
    this.$('saveBtn').addEventListener('click', () => this.save(false));
    this.$('deleteBtn').addEventListener('click', () => this.deleteNote());
    this.$('translateBtn').addEventListener('click', () => this.translate());
    this.$('copyBtn').addEventListener('click', () => this.copyTranslation());
    this.$('saveTranslationBtn').addEventListener('click', () => this.saveTranslation());
    this.$('searchBox').addEventListener('input', () => this.renderList());
    for (const id of ['noteTitle', 'noteContent']) {
      this.$(id).addEventListener('input', () => this.onEdit());
    }
    document.addEventListener('keydown', event => {
      const inField = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault(); this.$('searchBox').focus();
      } else if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
        event.preventDefault(); this.save(false);
      } else if (!inField && !event.metaKey && !event.ctrlKey && event.key.toLowerCase() === 'n') {
        event.preventDefault(); this.newNote();
      }
    });
  }

  async api(url, options = {}) {
    let response;
    try { response = await fetch(url, options); }
    catch { throw new Error('Network unavailable. Check your connection.'); }
    let body = null;
    if (response.status !== 204) {
      try { body = await response.json(); } catch { /* malformed response */ }
    }
    if (!response.ok) throw new Error(body?.error || `Request failed (${response.status})`);
    return body;
  }

  async load() {
    try {
      this.notes = await this.api('/api/notes');
      this.renderList();
    } catch (error) { this.toast(error.message, true); }
  }

  renderList() {
    const list = this.$('notesList');
    const query = this.$('searchBox').value.toLocaleLowerCase().trim();
    const filtered = this.notes.filter(n => (n.title + ' ' + n.content).toLocaleLowerCase().includes(query));
    this.$('noteCount').textContent = String(this.notes.length);
    list.replaceChildren();
    if (!filtered.length) {
      const empty = document.createElement('div');
      empty.className = 'list-empty';
      empty.textContent = query ? 'No notes match your search.' : 'No notes yet. Start with one small thought.';
      list.append(empty);
      return;
    }
    for (const note of filtered) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'note-item' + (this.current?.id === note.id ? ' active' : '');
      if (this.current?.id === note.id) button.setAttribute('aria-current', 'true');
      const title = document.createElement('span'); title.className = 'note-item-title'; title.textContent = note.title || 'Untitled';
      const preview = document.createElement('span'); preview.className = 'note-item-preview'; preview.textContent = note.content || 'A blank page';
      const date = document.createElement('span'); date.className = 'note-item-date'; date.textContent = this.formatDate(note.updated_at);
      button.append(title, preview, date);
      button.addEventListener('click', () => this.select(note.id));
      list.append(button);
    }
  }

  formatDate(value) {
    if (!value) return 'Just now';
    const date = new Date(value.endsWith('Z') || /[+-]\d\d:\d\d$/.test(value) ? value : value + 'Z');
    if (Number.isNaN(date.getTime())) return 'Just now';
    const days = Math.floor((Date.now() - date.getTime()) / 86400000);
    if (days <= 0) return 'Today';
    if (days === 1) return 'Yesterday';
    return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(date);
  }

  async flush() {
    clearTimeout(this.timer);
    if (this.current?.dirty) await this.save(true);
    await this.queue;
  }

  async select(id) {
    if (this.current?.id === id) return;
    await this.flush();
    const note = this.notes.find(n => n.id === id);
    if (!note) return;
    this.current = { ...note, dirty: false, revision: 0 };
    this.showEditor();
  }

  async newNote() {
    await this.flush();
    this.current = { id: null, title: '', content: '', dirty: false, revision: 0, updated_at: null };
    this.showEditor();
    this.$('noteTitle').focus();
  }

  showEditor() {
    const note = this.current;
    this.$('emptyState').hidden = true;
    this.$('editorView').hidden = false;
    this.$('noteTitle').value = note.title || '';
    this.$('noteContent').value = note.content || '';
    this.$('deleteBtn').hidden = !note.id;
    this.$('editedAt').textContent = this.formatDate(note.updated_at);
    this.$('crumbTitle').textContent = note.title || 'Untitled';
    this.renderWords();
    this.clearTranslation();
    this.status('Ready');
    this.renderList();
  }

  onEdit() {
    if (!this.current) return;
    this.current.title = this.$('noteTitle').value;
    this.current.content = this.$('noteContent').value;
    this.current.dirty = true;
    this.current.revision++;
    this.$('crumbTitle').textContent = this.current.title.trim() || 'Untitled';
    this.renderWords();
    this.clearTranslation();
    this.status('Unsaved changes', 'dirty');
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.save(true), 1000);
  }

  renderWords() {
    const words = this.$('noteContent').value.trim().match(/[^\s]+/g) || [];
    this.$('wordCount').textContent = `${words.length} ${words.length === 1 ? 'word' : 'words'}`;
  }

  status(label, type = '') {
    const element = this.$('saveStatus');
    element.className = 'save-status' + (type ? ' ' + type : '');
    element.lastChild.textContent = ' ' + label;
  }

  save(auto) {
    clearTimeout(this.timer);
    const draft = this.current;
    if (!draft) return Promise.resolve();
    const title = draft.title.trim();
    const content = draft.content.trim();
    if (!title && !content) {
      if (!auto) this.toast('Write a title or some content before saving.', true);
      return Promise.resolve();
    }
    if (!draft.dirty && draft.id) {
      if (!auto) this.toast('Your note is already saved.');
      return this.queue;
    }
    const revision = draft.revision;
    const payload = { title: title || 'Untitled', content };
    this.status('Saving…', 'dirty');
    this.queue = this.queue.catch(() => {}).then(async () => {
      const id = draft.id;
      try {
        const saved = await this.api(id ? `/api/notes/${id}` : '/api/notes', {
          method: id ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        draft.id = saved.id;
        draft.updated_at = saved.updated_at;
        if (draft.revision === revision) draft.dirty = false;
        const i = this.notes.findIndex(n => n.id === saved.id);
        if (i >= 0) this.notes[i] = saved; else this.notes.unshift(saved);
        this.notes.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
        if (this.current === draft) {
          this.$('deleteBtn').hidden = false;
          this.$('editedAt').textContent = this.formatDate(saved.updated_at);
          this.status(draft.dirty ? 'Unsaved changes' : 'Saved', draft.dirty ? 'dirty' : '');
        }
        this.renderList();
        if (!auto) this.toast('Note saved.');
      } catch (error) {
        if (this.current === draft) this.status('Save failed', 'error');
        this.toast(error.message, true);
        throw error;
      }
    });
    return this.queue;
  }

  async deleteNote() {
    const note = this.current;
    if (!note?.id) return;
    if (!window.confirm(`Delete “${note.title || 'Untitled'}”? This cannot be undone.`)) return;
    clearTimeout(this.timer);
    try {
      await this.queue.catch(() => {});
      await this.api(`/api/notes/${note.id}`, { method: 'DELETE' });
      this.notes = this.notes.filter(n => n.id !== note.id);
      this.current = null;
      this.$('editorView').hidden = true;
      this.$('emptyState').hidden = false;
      this.$('crumbTitle').textContent = 'Untitled';
      this.status('Ready');
      this.renderList();
      this.toast('Note deleted.');
    } catch (error) { this.toast(error.message, true); }
  }

  clearTranslation() {
    this.translation = null;
    this.$('translationResult').hidden = true;
    this.$('translationEmpty').hidden = false;
  }

  async translate() {
    if (!this.current) return;
    const title = this.$('noteTitle').value.trim();
    const content = this.$('noteContent').value.trim();
    if (!title && !content) { this.toast('Write something before translating.', true); return; }
    const button = this.$('translateBtn');
    button.disabled = true;
    button.querySelector('span').textContent = 'Translating…';
    const revision = this.current.revision;
    const draft = this.current;
    try {
      const result = await this.api('/api/translate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content, target_language: this.$('targetLanguage').value }),
      });
      if (this.current !== draft || this.current.revision !== revision) return;
      this.translation = result;
      this.$('resultLanguage').textContent = result.target_language.toUpperCase();
      this.$('resultTitle').textContent = result.title || 'Untitled';
      this.$('resultContent').textContent = result.content;
      this.$('translationEmpty').hidden = true;
      this.$('translationResult').hidden = false;
      this.toast('Translation is ready.');
    } catch (error) { this.toast(error.message, true); }
    finally { button.disabled = false; button.querySelector('span').textContent = 'Translate note'; }
  }

  async copyTranslation() {
    if (!this.translation) return;
    try {
      await navigator.clipboard.writeText(`${this.translation.title}\n\n${this.translation.content}`);
      this.toast('Translation copied to clipboard.');
    } catch { this.toast('Clipboard unavailable. Select and copy the text instead.', true); }
  }

  async saveTranslation() {
    if (!this.translation) return;
    const button = this.$('saveTranslationBtn');
    button.disabled = true;
    try {
      await this.flush();
      const saved = await this.api('/api/notes', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: this.translation.title || 'Untitled', content: this.translation.content }),
      });
      this.notes.unshift(saved);
      this.current = { ...saved, dirty: false, revision: 0 };
      this.showEditor();
      this.toast('Translation saved as a new note.');
    } catch (error) { this.toast(error.message, true); }
    finally { button.disabled = false; }
  }

  toast(message, error = false) {
    const toast = this.$('toast');
    toast.textContent = message;
    toast.className = 'toast' + (error ? ' error' : '');
    toast.hidden = false;
    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => toast.hidden = true, 4300);
  }
}
new MarginApp();
