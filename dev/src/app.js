// ================================
// App State
// ================================
const AppState = {
  currentScreen: 'landing',
  selectedIndustry: null,
  selectedRole: null,
  selectedTask: null
};

// ================================
// Navigation
// ================================
function navigateToScreen(screenName) {
  // Hide all screens
  document.querySelectorAll('.screen').forEach(screen => {
    screen.classList.remove('active');
  });
  
  // Show target screen
  const targetScreen = document.getElementById(screenName);
  if (targetScreen) {
    targetScreen.classList.add('active');
    AppState.currentScreen = screenName;
    
    // Scroll to top immediately
    window.scrollTo(0, 0);
    
    // Render content based on screen
    if (screenName === 'industries') {
      renderIndustries();
    } else if (screenName === 'roles') {
      renderRoles();
    } else if (screenName === 'tasks') {
      renderTasks();
    }
  }
}

// ================================
// Render Industries
// ================================
function renderIndustries() {
  const grid = document.getElementById('industries-grid');
  grid.innerHTML = '';
  
  APP_DATA.industries.forEach(industry => {
    const card = document.createElement('div');
    card.className = industry.active ? 'card card-clickable role-card' : 'card';
    card.style.opacity = industry.active ? '1' : '0.5';
    card.style.cursor = industry.active ? 'pointer' : 'not-allowed';
    
    if (industry.active) {
      card.onclick = () => selectIndustry(industry.id);
    }
    
    card.innerHTML = `
      <div class="card-icon">${industry.active ? '✓' : '🔒'}</div>
      <h3>${industry.name}</h3>
      ${industry.active 
        ? '<span class="badge badge-primary">Доступно</span>'
        : '<span class="badge badge-warning">Скоро</span>'
      }
    `;
    
    grid.appendChild(card);
  });
}

function selectIndustry(industryId) {
  AppState.selectedIndustry = industryId;
  navigateToScreen('roles');
}

// ================================
// Render Roles
// ================================
function renderRoles() {
  const grid = document.getElementById('roles-grid');
  grid.innerHTML = '';
  
  Object.values(APP_DATA.roles).forEach(role => {
    const card = document.createElement('div');
    card.className = 'card card-clickable role-card';
    card.onclick = () => selectRole(role.id);
    
    card.innerHTML = `
      <div class="card-icon">${role.icon}</div>
      <h3 style="margin-bottom: 8px;">${role.name}</h3>
      <p class="role-tagline">${role.tagline}</p>
      <div style="margin-top: 12px;">
        <span class="badge badge-primary">${role.tasks.length} задач</span>
      </div>
    `;
    
    grid.appendChild(card);
  });
}

function selectRole(roleId) {
  AppState.selectedRole = roleId;
  navigateToScreen('tasks');
}

// ================================
// Render Tasks
// ================================
function renderTasks() {
  const role = APP_DATA.roles[AppState.selectedRole];
  if (!role) return;
  
  // Update role info
  document.getElementById('current-role-icon').textContent = role.icon;
  document.getElementById('current-role-name').textContent = role.name;
  document.getElementById('current-role-tagline').textContent = role.tagline;
  
  // Render tasks list
  const tasksList = document.getElementById('tasks-list');
  tasksList.innerHTML = '';
  
  role.tasks.forEach(task => {
    const taskItem = document.createElement('div');
    taskItem.className = `task-item ${task.recommended ? 'recommended' : ''}`;
    taskItem.onclick = () => selectTask(task.id);
    
    const badges = [];
    if (task.recommended) {
      badges.push('<span class="badge badge-gradient">⭐ Рекомендуем</span>');
    }
    if (task.frequency) {
      badges.push(`<span class="badge badge-primary">${task.frequency}</span>`);
    }
    if (task.pain === 'high') {
      badges.push('<span class="badge badge-error">Высокая боль</span>');
    }
    if (task.wow === 'high') {
      badges.push('<span class="badge badge-accent">Вау-эффект</span>');
    }
    
    taskItem.innerHTML = `
      <div>
        <h4 style="margin: 0 0 4px 0;">${task.name}</h4>
        ${task.description ? `<p style="margin: 0; font-size: 14px; color: var(--text-secondary);">${task.description}</p>` : ''}
      </div>
      <div class="task-badges">
        ${badges.join('')}
      </div>
    `;
    
    tasksList.appendChild(taskItem);
  });
}

function selectTask(taskId) {
  AppState.selectedTask = taskId;
  
  const role = APP_DATA.roles[AppState.selectedRole];
  const task = role.tasks.find(t => t.id === taskId);
  
  if (!task) return;
  
  // Update task interface
  document.getElementById('current-task-breadcrumb').textContent = task.name;
  document.getElementById('task-title').textContent = task.name;
  document.getElementById('task-description').textContent = task.description || '';
  
  navigateToScreen('task-interface');
}

// ================================
// Execute Task
// ================================
function executeTask() {
  const role = APP_DATA.roles[AppState.selectedRole];
  const task = role.tasks.find(t => t.id === AppState.selectedTask);
  
  if (!task) return;
  
  // Navigate to result screen
  navigateToScreen('result');
  
  // Show loading
  document.getElementById('loading-state').classList.remove('hidden');
  document.getElementById('result-content').classList.add('hidden');
  
  // Simulate AI processing (2 seconds)
  setTimeout(() => {
    showResult(role, task);
  }, 2000);
}

function showResult(role, task) {
  // Hide loading
  document.getElementById('loading-state').classList.add('hidden');
  
  // Update result
  document.getElementById('result-role-name').textContent = role.name;
  
  // Check if task has mockResponse
  if (task.mockResponse) {
    document.getElementById('result-summary').textContent = task.mockResponse.summary;
    document.getElementById('result-text').textContent = task.mockResponse.content;
  } else {
    // Generic response for tasks without mockResponse
    document.getElementById('result-summary').textContent = 'Анализирую данные вашей компании...';
    document.getElementById('result-text').textContent = `
📊 АНАЛИЗ ЗАВЕРШЁН

Я изучил контекст вашей компании и подготовил рекомендации для задачи "${task.name}".

В полной версии svaib здесь будет:
• Детальный анализ ситуации
• Конкретные действия с приоритетами
• Готовые шаблоны документов
• Метрики для отслеживания результата

💡 Это демо-версия. Чтобы получить настоящие результаты с учётом данных вашей компании, зарегистрируйтесь ниже.
    `;
  }
  
  // Show result
  document.getElementById('result-content').classList.remove('hidden');
  
  // Scroll to top immediately
  window.scrollTo(0, 0);
}

// ================================
// Copy Result
// ================================
function copyResult() {
  const resultText = document.getElementById('result-text').textContent;
  
  navigator.clipboard.writeText(resultText).then(() => {
    // Show success feedback
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = '✓ Скопировано!';
    btn.style.background = 'var(--success)';
    btn.style.color = 'white';
    
    setTimeout(() => {
      btn.textContent = originalText;
      btn.style.background = '';
      btn.style.color = '';
    }, 2000);
  }).catch(err => {
    alert('Не удалось скопировать. Попробуйте выделить текст вручную.');
  });
}

// ================================
// Initialize
// ================================
document.addEventListener('DOMContentLoaded', () => {
  console.log('svaib prototype loaded');
  console.log('Available roles:', Object.keys(APP_DATA.roles));
  console.log('Total tasks:', Object.values(APP_DATA.roles).reduce((sum, role) => sum + role.tasks.length, 0));
});

// ================================
// Keyboard shortcuts (for testing)
// ================================
document.addEventListener('keydown', (e) => {
  // Ctrl/Cmd + K to go to roles
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    AppState.selectedIndustry = 'it';
    navigateToScreen('roles');
  }
});
