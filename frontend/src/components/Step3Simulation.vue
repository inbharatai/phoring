<template>
  <div class="simulation-panel">
    <!-- Top Control Bar -->
    <div class="control-bar">
      <div class="status-group">
        <!-- Twitter platformprogress -->
        <div class="platform-status twitter":class="{ active: runStatus.twitter_running, completed: runStatus.twitter_completed }">
          <div class="platform-header">
            <svg class="platform-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
            </svg>
            <span class="platform-name">Info Plaza</span>
            <span v-if="runStatus.twitter_completed" class="status-badge">
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </span>
          </div>
          <div class="platform-stats">
            <span class="stat">
              <span class="stat-label">ROUND</span>
              <span class="stat-value mono">{{ runStatus.twitter_current_round || 0 }}<span class="stat-total">/{{ runStatus.total_rounds || maxRounds || '-' }}</span></span>
            </span>
            <span class="stat">
              <span class="stat-label">Elapsed Time</span>
              <span class="stat-value mono">{{ twitterElapsedTime }}</span>
            </span>
            <span class="stat">
              <span class="stat-label">ACTS</span>
              <span class="stat-value mono">{{ runStatus.twitter_actions_count || 0 }}</span>
            </span>
          </div>
          <!-- hint -->
          <div class="actions-tooltip">
            <div class="tooltip-title">Available Actions</div>
            <div class="tooltip-actions">
              <span class="tooltip-action">POST</span>
              <span class="tooltip-action">LIKE</span>
              <span class="tooltip-action">REPOST</span>
              <span class="tooltip-action">QUOTE</span>
              <span class="tooltip-action">FOLLOW</span>
              <span class="tooltip-action">IDLE</span>
            </div>
          </div>
        </div>
        
        <!-- Reddit platformprogress -->
        <div class="platform-status reddit":class="{ active: runStatus.reddit_running, completed: runStatus.reddit_completed }">
          <div class="platform-header">
            <svg class="platform-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
            </svg>
            <span class="platform-name">Topic Community</span>
            <span v-if="runStatus.reddit_completed" class="status-badge">
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </span>
          </div>
          <div class="platform-stats">
            <span class="stat">
              <span class="stat-label">ROUND</span>
              <span class="stat-value mono">{{ runStatus.reddit_current_round || 0 }}<span class="stat-total">/{{ runStatus.total_rounds || maxRounds || '-' }}</span></span>
            </span>
            <span class="stat">
              <span class="stat-label">Elapsed Time</span>
              <span class="stat-value mono">{{ redditElapsedTime }}</span>
            </span>
            <span class="stat">
              <span class="stat-label">ACTS</span>
              <span class="stat-value mono">{{ runStatus.reddit_actions_count || 0 }}</span>
            </span>
          </div>
          <!-- hint -->
          <div class="actions-tooltip">
            <div class="tooltip-title">Available Actions</div>
            <div class="tooltip-actions">
              <span class="tooltip-action">POST</span>
              <span class="tooltip-action">COMMENT</span>
              <span class="tooltip-action">LIKE</span>
              <span class="tooltip-action">DISLIKE</span>
              <span class="tooltip-action">SEARCH</span>
              <span class="tooltip-action">TREND</span>
              <span class="tooltip-action">FOLLOW</span>
              <span class="tooltip-action">MUTE</span>
              <span class="tooltip-action">REFRESH</span>
              <span class="tooltip-action">IDLE</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Consensus Validation Config Panel — visible once validators are loaded -->
      <Transition name="consensus-panel">
        <div v-if="validatorsLoaded" class="consensus-config-panel" :class="{ 'panel-ready': phase === 2 }">
          <div class="consensus-section-label">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>
            <span>AI Validation Configuration</span>
          </div>
          <div class="consensus-toggle-row">
            <label class="consensus-toggle" :title="availableValidators.filter(v=>v.configured).length < 2 ? 'Configure a second AI provider to enable true consensus' : ''">
              <input type="checkbox" v-model="consensusEnabled" :disabled="availableValidators.filter(v=>v.configured).length < 2" />
              <span class="toggle-track"><span class="toggle-thumb"></span></span>
              <span class="toggle-label">Multi-AI Consensus Validation</span>
            </label>
            <span class="consensus-hint" v-if="!consensusEnabled">Report will use single-AI generation</span>
            <span class="consensus-hint active" v-else>{{ selectedValidators.length }} validator{{ selectedValidators.length !== 1 ? 's' : '' }} selected</span>
          </div>
          <div v-if="availableValidators.filter(v=>v.configured).length < 2" class="consensus-single-warn">
            ⚠ Only 1 AI provider configured — add a 2nd validator (Anthropic/Gemini) to enable true multi-model consensus
          </div>
          <div v-if="consensusEnabled" class="validator-selector">
            <div 
              v-for="v in availableValidators" 
              :key="v.index"
              class="validator-chip"
              :class="{ selected: selectedValidators.includes(v.index), disabled: !v.configured }"
              @click="toggleValidator(v)"
            >
              <span class="chip-index">#{{ v.index }}</span>
              <span class="chip-model">{{ v.configured ? v.model : 'Not configured' }}</span>
              <span class="chip-label">{{ v.label }}</span>
              <span v-if="selectedValidators.includes(v.index)" class="chip-check">
                <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
              </span>
            </div>
          </div>
          <div v-if="consensusEnabled && selectedValidators.length > 0" class="consensus-summary">
            Report will be cross-validated by {{ selectedValidators.length }} AI model{{ selectedValidators.length !== 1 ? 's' : '' }}
          </div>
        </div>
      </Transition>

      <div class="action-controls">
        <button 
          class="action-btn primary"
          :disabled="phase!== 2 || isGeneratingReport"
          @click="handleNextStep"
        >
          <span v-if="isGeneratingReport" class="loading-spinner-small"></span>
          {{ isGeneratingReport? '...': 'Start Generating Result Report' }} 
          <span v-if="!isGeneratingReport" class="arrow-icon">→</span>
        </button>
      </div>
    </div>

    <!-- Main Content: Dual Timeline -->
    <div class="main-content-area" ref="scrollContainer">
      <!-- Timeline Header -->
      <div class="timeline-header" v-if="allActions.length > 0">
        <div class="timeline-stats">
          <span class="total-count">TOTAL EVENTS: <span class="mono">{{ allActions.length }}</span></span>
          <span class="platform-breakdown">
            <span class="breakdown-item twitter">
              <svg class="mini-icon" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
              <span class="mono">{{ twitterActionsCount }}</span>
            </span>
            <span class="breakdown-divider">/</span>
            <span class="breakdown-item reddit">
              <svg class="mini-icon" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
              <span class="mono">{{ redditActionsCount }}</span>
            </span>
          </span>
        </div>
      </div>
      
      <!-- Timeline Feed -->
      <div class="timeline-feed">
        <div class="timeline-axis"></div>
        
        <TransitionGroup name="timeline-item">
          <div 
            v-for="action in chronologicalActions" 
            :key="action._uniqueId || action.id || `${action.timestamp}-${action.agent_id}`" 
            class="timeline-item"
            :class="action._isGeoEvent ? 'geopolitical' : action.platform"
          >
            <div class="timeline-marker">
              <div class="marker-dot"></div>
            </div>

            <!-- Geopolitical Event Card -->
            <div v-if="action._isGeoEvent" class="timeline-card geo-event-card" :class="'severity-' + action.geo.severity">
              <div class="geo-event-header">
                <div class="geo-event-badge">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                  <span>GEOPOLITICAL EVENT</span>
                </div>
                <span class="geo-severity-tag" :class="'sev-' + action.geo.severity">{{ action.geo.severity?.toUpperCase() }}</span>
              </div>
              <div class="geo-event-body">
                <div class="geo-event-category">{{ action.geo.category?.replace(/_/g, ' ') }}</div>
                <div class="geo-event-title">{{ action.geo.title }}</div>
                <p class="geo-event-desc">{{ action.geo.description }}</p>
                <div class="geo-event-meta">
                  <span class="geo-impact" :class="action.geo.impact_factor < 0 ? 'negative' : 'positive'">
                    Impact: {{ action.geo.impact_factor > 0 ? '+' : '' }}{{ action.geo.impact_factor }}
                  </span>
                  <span v-if="action.geo.affected_entity_types?.length" class="geo-affected">
                    Affects: {{ action.geo.affected_entity_types.join(', ') }}
                  </span>
                </div>
              </div>
              <div class="card-footer">
                <span class="time-tag">R{{ action.geo.trigger_round }} • Disruption Event</span>
              </div>
            </div>

            <!-- Regular Action Card -->
            <div v-else class="timeline-card">
              <div class="card-header">
                <div class="agent-info">
                  <div class="avatar-placeholder">{{ (action.agent_name || 'A')[0] }}</div>
                  <span class="agent-name">{{ action.agent_name }}</span>
                </div>
                
                <div class="header-meta">
                  <div class="platform-indicator">
                    <svg v-if="action.platform === 'twitter'" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
                    <svg v-else viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
                  </div>
                  <div class="action-badge":class="getActionTypeClass(action.action_type)">
                    {{ getActionTypeLabel(action.action_type) }}
                  </div>
                </div>
              </div>
              
              <div class="card-body">
                <!-- CREATE_POST: publishpost -->
                <div v-if="action.action_type === 'CREATE_POST' && action.action_args?.content" class="content-text main-text">
                  {{ action.action_args.content }}
                </div>

                <!-- QUOTE_POST: quotepost -->
                <template v-if="action.action_type === 'QUOTE_POST'">
                  <div v-if="action.action_args?.quote_content" class="content-text">
                    {{ action.action_args.quote_content }}
                  </div>
                  <div v-if="action.action_args?.original_content" class="quoted-block">
                    <div class="quote-header">
                      <svg class="icon-small" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
                      <span class="quote-label">@{{ action.action_args.original_author_name || 'User' }}</span>
                    </div>
                    <div class="quote-text">
                      {{ truncateContent(action.action_args.original_content, 150) }}
                    </div>
                  </div>
                </template>

                <!-- REPOST: repostpost -->
                <template v-if="action.action_type === 'REPOST'">
                  <div class="repost-info">
                    <svg class="icon-small" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"></polyline><path d="M3 11V9a4 4 0 0 1 4-4h14"></path><polyline points="7 23 3 19 7 15"></polyline><path d="M21 13v2a4 4 0 0 1-4 4H3"></path></svg>
                    <span class="repost-label">Reposted from @{{ action.action_args?.original_author_name || 'User' }}</span>
                  </div>
                  <div v-if="action.action_args?.original_content" class="repost-content">
                    {{ truncateContent(action.action_args.original_content, 200) }}
                  </div>
                </template>

                <!-- LIKE_POST: likepost -->
                <template v-if="action.action_type === 'LIKE_POST'">
                  <div class="like-info">
                    <svg class="icon-small filled" viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
                    <span class="like-label">Liked @{{ action.action_args?.post_author_name || 'User' }}'s post</span>
                  </div>
                  <div v-if="action.action_args?.post_content" class="liked-content">
                    "{{ truncateContent(action.action_args.post_content, 120) }}"
                  </div>
                </template>

                <!-- CREATE_COMMENT: comment -->
                <template v-if="action.action_type === 'CREATE_COMMENT'">
                  <div v-if="action.action_args?.content" class="content-text">
                    {{ action.action_args.content }}
                  </div>
                  <div v-if="action.action_args?.post_id" class="comment-context">
                    <svg class="icon-small" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
                    <span>Reply to post #{{ action.action_args.post_id }}</span>
                  </div>
                </template>

                <!-- SEARCH_POSTS: searchpost -->
                <template v-if="action.action_type === 'SEARCH_POSTS'">
                  <div class="search-info">
                    <svg class="icon-small" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                    <span class="search-label">Search Query:</span>
                    <span class="search-query">"{{ action.action_args?.query || '' }}"</span>
                  </div>
                </template>

                <!-- FOLLOW: followuser -->
                <template v-if="action.action_type === 'FOLLOW'">
                  <div class="follow-info">
                    <svg class="icon-small" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line></svg>
                    <span class="follow-label">Followed @{{ action.action_args?.target_user || action.action_args?.user_id || 'User' }}</span>
                  </div>
                </template>

                <!-- UPVOTE / DOWNVOTE -->
                <template v-if="action.action_type === 'UPVOTE_POST' || action.action_type === 'DOWNVOTE_POST'">
                  <div class="vote-info">
                    <svg v-if="action.action_type === 'UPVOTE_POST'" class="icon-small" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"></polyline></svg>
                    <svg v-else class="icon-small" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    <span class="vote-label">{{ action.action_type === 'UPVOTE_POST'? 'Upvoted': 'Downvoted' }} Post</span>
                  </div>
                  <div v-if="action.action_args?.post_content" class="voted-content">
                    "{{ truncateContent(action.action_args.post_content, 120) }}"
                  </div>
                </template>

                <!-- DO_NOTHING: () -->
                <template v-if="action.action_type === 'DO_NOTHING'">
                  <div class="idle-info">
                    <svg class="icon-small" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                    <span class="idle-label">Action Skipped</span>
                  </div>
                </template>

                <!-- fallback: N/Atype content N/AProcess -->
                <div v-if="!['CREATE_POST', 'QUOTE_POST', 'REPOST', 'LIKE_POST', 'CREATE_COMMENT', 'SEARCH_POSTS', 'FOLLOW', 'UPVOTE_POST', 'DOWNVOTE_POST', 'DO_NOTHING'].includes(action.action_type) && action.action_args?.content" class="content-text">
                  {{ action.action_args.content }}
                </div>
              </div>

              <div class="card-footer">
                <span class="time-tag">R{{ action.round_num }} • {{ formatActionTime(action.timestamp) }}</span>
                <!-- Platform tag removed as it is in header now -->
              </div>
            </div>
          </div>
        </TransitionGroup>

        <div v-if="allActions.length === 0" class="waiting-state">
          <div class="pulse-ring"></div>
          <span>Waiting for agent actions...</span>
        </div>
      </div>
    </div>

    <!-- Bottom Info / Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span class="log-title">SIMULATION MONITOR</span>
        <span class="log-id">{{ simulationId || 'NO_SIMULATION' }}</span>
      </div>
      <div class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in systemLogs":key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { 
  startSimulation, 
  stopSimulation,
  getRunStatus, 
  getRunStatusDetail,
  getSimulationConfig
} from '../api/simulation'
import { generateReport, getValidators } from '../api/report'

const props = defineProps({
  simulationId: String,
  maxRounds: Number, // Step2 max round 
  minutesPerRound: {
    type: Number,
    default: 30 // default round30 
  },
  projectData: Object,
  graphData: Object,
  systemLogs: Array
})

const emit = defineEmits(['go-back', 'next-step', 'add-log', 'update-status'])

const router = useRouter()

// State
const isGeneratingReport = ref(false)
const phase = ref(0) // 0: N/Astarted, 1: row, 2: already complete
const isStarting = ref(false)
const isStopping = ref(false)
const startError = ref(null)
const runStatus = ref({})
const allActions = ref([]) // all ()
const actionIds = ref(new Set()) // ID 
const scrollContainer = ref(null)
const scheduledEvents = ref([]) // geopolitical disruption events

// Consensus validation config
const consensusEnabled = ref(false)
const availableValidators = ref([])
const selectedValidators = ref([])
const validatorsLoaded = ref(false)

// Computed
// Merge agent actions + geopolitical events into timeline
const chronologicalActions = computed(() => {
  // Build event markers from scheduled events, keyed by trigger_round
  const eventMarkers = scheduledEvents.value.map((evt, idx) => ({
    _uniqueId: `geo_event_${idx}`,
    _isGeoEvent: true,
    round_num: evt.trigger_round,
    timestamp: new Date(0).toISOString(), // sort to beginning of that round
    platform: 'geopolitical',
    agent_name: 'GEOPOLITICAL EVENT',
    action_type: 'GEO_EVENT',
    geo: evt
  }))
  return [...allActions.value, ...eventMarkers]
})

// platform 
const twitterActionsCount = computed(() => {
  return allActions.value.filter(a => a.platform === 'twitter').length
})

const redditActionsCount = computed(() => {
  return allActions.value.filter(a => a.platform === 'reddit').length
})

// format simulation time( round round)
const formatElapsedTime = (currentRound) => {
  if (!currentRound || currentRound <= 0) return '0h 0m'
  const totalMinutes = currentRound * props.minutesPerRound
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return `${hours}h ${minutes}m`
}

// Twitterplatform simulation time
const twitterElapsedTime = computed(() => {
  return formatElapsedTime(runStatus.value.twitter_current_round || 0)
})

// Redditplatform simulation time
const redditElapsedTime = computed(() => {
  return formatElapsedTime(runStatus.value.reddit_current_round || 0)
})

// Methods
const addLog = (msg) => {
  emit('add-log', msg)
}

// resetallstatus( new simulation)
const resetAllState = () => {
  phase.value = 0
  runStatus.value = {}
  allActions.value = []
  actionIds.value = new Set()
  prevTwitterRound.value = 0
  prevRedditRound.value = 0
  startError.value = null
  isStarting.value = false
  isStopping.value = false
  stopPolling() // stop exists round 
}

// simulation
const doStartSimulation = async () => {
  if (!props.simulationId) {
    addLog('error: simulationId')
    return
  }
  
  // resetallstatus, Ensure simulation influence
  resetAllState()
  
  isStarting.value = true
  startError.value = null
  addLog(' platform rowsimulation...')
  emit('update-status', 'processing')
  
  try {
    const params = {
      simulation_id: props.simulationId,
      platform: 'parallel',
      force: true, // newstart
      enable_graph_memory_update: true // graphUpdate
    }
    
    if (props.maxRounds) {
      params.max_rounds = props.maxRounds
      addLog(`settings max simulation round: ${props.maxRounds}`)
    }
    
    addLog('already graph update mode')
    
    const res = await startSimulation(params)
    
    if (res.success && res.data) {
      if (res.data.force_restarted) {
        addLog('✓ already cleaned up old simulation log, starting new simulation')
      }
      addLog('✓ simulation success')
      addLog(` ├─ PID: ${res.data.process_pid || '-'}`)
      
      phase.value = 1
      runStatus.value = res.data
      
      startStatusPolling()
      startDetailPolling()
    } else {
      startError.value = res.error || ' failed'
      addLog(`✗ failed: ${res.error || 'unknown error'}`)
      emit('update-status', 'error')
    }
  } catch (err) {
    startError.value = err.message
    addLog(`✗: ${err.message}`)
    emit('update-status', 'error')
  } finally {
    isStarting.value = false
  }
}

// stop simulation
const handleStopSimulation = async () => {
  if (!props.simulationId) return
  
  isStopping.value = true
  addLog(' stop simulation...')
  
  try {
    const res = await stopSimulation({ simulation_id: props.simulationId })
    
    if (res.success) {
      addLog('✓ simulation already stopped')
      phase.value = 2
      stopPolling()
      emit('update-status', 'completed')
    } else {
      addLog(`stop failed: ${res.error || 'unknown error'}`)
    }
  } catch (err) {
    addLog(`stop: ${err.message}`)
  } finally {
    isStopping.value = false
  }
}

// round status
let statusTimer = null
let detailTimer = null

const startStatusPolling = () => {
  statusTimer = setInterval(fetchRunStatus, 2000)
}

const startDetailPolling = () => {
  detailTimer = setInterval(fetchRunStatusDetail, 3000)
}

const stopPolling = () => {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
  if (detailTimer) {
    clearInterval(detailTimer)
    detailTimer = null
  }
}

// platform round, outputlog
const prevTwitterRound = ref(0)
const prevRedditRound = ref(0)

const fetchRunStatus = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getRunStatus(props.simulationId)
    
    if (res.success && res.data) {
      const data = res.data
      
      runStatus.value = data
      
      // Detect backend state reset (server restart / orphan recovery)
      // If backend says idle but we were in phase 1 (running), the simulation was lost
      if (data.runner_status === 'idle' && phase.value === 1) {
        addLog('⚠ simulation lost — server may have restarted')
        addLog('  please restart the simulation')
        phase.value = 0
        stopPolling()
        // Clear stale cached actions from previous run
        allActions.value = []
        actionIds.value = new Set()
        emit('update-status', 'error')
        return
      }
      
      // Detect failed simulation
      if (data.runner_status === 'failed') {
        addLog(`✗ simulation failed: ${data.error || 'unknown error'}`)
        phase.value = 0
        stopPolling()
        startError.value = data.error || 'Simulation failed'
        emit('update-status', 'error')
        return
      }
      
      // platform round outputlog
      if (data.twitter_current_round > prevTwitterRound.value) {
        addLog(`[Plaza] R${data.twitter_current_round}/${data.total_rounds} | T:${data.twitter_simulated_hours || 0}h | A:${data.twitter_actions_count}`)
        prevTwitterRound.value = data.twitter_current_round
      }
      
      if (data.reddit_current_round > prevRedditRound.value) {
        addLog(`[Community] R${data.reddit_current_round}/${data.total_rounds} | T:${data.reddit_simulated_hours || 0}h | A:${data.reddit_actions_count}`)
        prevRedditRound.value = data.reddit_current_round
      }
      
      // check if simulation already complete( runner_status platform complete status)
      const isCompleted = data.runner_status === 'completed' || data.runner_status === 'stopped'
      
      // Check: if Update runner_status, platformalready reportcomplete
      // twitter_completed reddit_completed status 
      const platformsCompleted = checkPlatformsCompleted(data)
      
      if (isCompleted || platformsCompleted) {
        if (platformsCompleted &&!isCompleted) {
          addLog('✓ all platform simulations already finished')
        }
        addLog('✓ simulation already complete')
        phase.value = 2
        stopPolling()
        emit('update-status', 'completed')
      }
    }
  } catch (err) {
    console.warn('Get rowstatusfailed:', err)
  }
}

// Check all platforms whether already complete
const checkPlatformsCompleted = (data) => {
  // if platformdata, return false
  if (!data) return false
  
  // Check platform completestatus
  const twitterCompleted = data.twitter_completed === true
  const redditCompleted = data.reddit_completed === true
  
  // if platform complete, Checkwhetherall platform complete 
  // actions_count platform whether (if count > 0 running true)
  const twitterEnabled = (data.twitter_actions_count > 0) || data.twitter_running || twitterCompleted
  const redditEnabled = (data.reddit_actions_count > 0) || data.reddit_running || redditCompleted
  
  // if platform, return false
  if (!twitterEnabled &&!redditEnabled) return false
  
  // Check all platform whether already complete
  if (twitterEnabled &&!twitterCompleted) return false
  if (redditEnabled &&!redditCompleted) return false
  
  return true
}

const fetchRunStatusDetail = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getRunStatusDetail(props.simulationId)
    
    if (res.success && res.data) {
      // Also update runStatus from detail response (has the same state fields)
      // This provides a second source of truth for round/progress data
      if (res.data.runner_status && res.data.runner_status !== 'idle') {
        runStatus.value = { ...runStatus.value, ...res.data }
      }
      
      // all_actions Getcomplete list
      const serverActions = res.data.all_actions || []
      
      // Detect server reset: if server has fewer actions than our cache,
      // the backend was restarted and old logs were cleaned up — sync fully
      if (serverActions.length < allActions.value.length && serverActions.length === 0 && allActions.value.length > 0) {
        allActions.value = []
        actionIds.value = new Set()
      }
      
      // addnew ()
      let newActionsAdded = 0
      serverActions.forEach(action => {
        // generate ID
        const actionId = action.id || `${action.timestamp}-${action.platform}-${action.agent_id}-${action.action_type}`
        
        if (!actionIds.value.has(actionId)) {
          actionIds.value.add(actionId)
          allActions.value.push({
            ...action,
            _uniqueId: actionId
          })
          newActionsAdded++
        }
      })
    }
  } catch (err) {
    console.warn('Getdetailedstatusfailed:', err)
  }
}

// Helpers
const getActionTypeLabel = (type) => {
  const labels = {
    'CREATE_POST': 'POST',
    'REPOST': 'REPOST',
    'LIKE_POST': 'LIKE',
    'CREATE_COMMENT': 'COMMENT',
    'LIKE_COMMENT': 'LIKE',
    'DO_NOTHING': 'IDLE',
    'FOLLOW': 'FOLLOW',
    'SEARCH_POSTS': 'SEARCH',
    'QUOTE_POST': 'QUOTE',
    'UPVOTE_POST': 'UPVOTE',
    'DOWNVOTE_POST': 'DOWNVOTE'
  }
  return labels[type] || type || 'UNKNOWN'
}

const getActionTypeClass = (type) => {
  const classes = {
    'CREATE_POST': 'badge-post',
    'REPOST': 'badge-action',
    'LIKE_POST': 'badge-action',
    'CREATE_COMMENT': 'badge-comment',
    'LIKE_COMMENT': 'badge-action',
    'QUOTE_POST': 'badge-post',
    'FOLLOW': 'badge-meta',
    'SEARCH_POSTS': 'badge-meta',
    'UPVOTE_POST': 'badge-action',
    'DOWNVOTE_POST': 'badge-action',
    'DO_NOTHING': 'badge-idle'
  }
  return classes[type] || 'badge-default'
}

const truncateContent = (content, maxLength = 100) => {
  if (!content) return ''
  if (content.length > maxLength) return content.substring(0, maxLength) + '...'
  return content
}

const formatActionTime = (timestamp) => {
  if (!timestamp) return ''
  try {
    return new Date(timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
}

const handleNextStep = async () => {
  if (!props.simulationId) {
    addLog('error: simulationId')
    return
  }
  
  if (isGeneratingReport.value) {
    addLog('reportgenerateplease already, please...')
    return
  }
  
  isGeneratingReport.value = true
  addLog(' reportgenerate...')
  
  // Build consensus config from user selections
  const consensusConfig = {
    enabled: consensusEnabled.value && selectedValidators.value.length > 0,
    validators: consensusEnabled.value ? [...selectedValidators.value] : []
  }
  
  if (consensusConfig.enabled) {
    const models = availableValidators.value
      .filter(v => selectedValidators.value.includes(v.index))
      .map(v => v.model)
    addLog(`Consensus validation: ON (${models.join(', ')})`)
  } else {
    addLog('Consensus validation: OFF')
  }
  
  try {
    const res = await generateReport({
      simulation_id: props.simulationId,
      force_regenerate: true,
      consensus_config: consensusConfig
    })
    
    if (res.success && res.data) {
      const reportId = res.data.report_id
      addLog(`✓ report generation task started: ${reportId}`)
      
      // reportpage
      router.push({ name: 'Report', params: { reportId } })
    } else {
      addLog(`✗ reportgeneratefailed: ${res.error || 'unknown error'}`)
      isGeneratingReport.value = false
    }
  } catch (err) {
    addLog(`✗ reportgenerate: ${err.message}`)
    isGeneratingReport.value = false
  }
}

// Scroll log to bottom
const logContent = ref(null)
watch(() => props.systemLogs?.length, () => {
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
})

// Fetch geopolitical events from simulation config
const fetchScheduledEvents = async () => {
  if (!props.simulationId) return
  try {
    const res = await getSimulationConfig(props.simulationId)
    if (res.success && res.data?.event_config?.scheduled_events) {
      scheduledEvents.value = res.data.event_config.scheduled_events
      if (scheduledEvents.value.length > 0) {
        addLog(`Loaded ${scheduledEvents.value.length} geopolitical disruption events`)
      }
    }
  } catch (err) {
    console.warn('Fetch geopolitical events failed:', err)
  }
}

// Fetch available validators for consensus config
const fetchValidators = async () => {
  try {
    const res = await getValidators()
    if (res.data?.success !== false && res.data?.data) {
      availableValidators.value = res.data.data
    } else if (res.success && res.data) {
      availableValidators.value = res.data
    }
    // Auto-select all configured validators and enable consensus if 2+ available
    const configured = availableValidators.value.filter(v => v.configured)
    if (configured.length > 0) {
      selectedValidators.value = configured.map(v => v.index)
      consensusEnabled.value = configured.length >= 2
    }
    validatorsLoaded.value = true
  } catch (err) {
    console.warn('Fetch validators failed:', err)
    validatorsLoaded.value = true
  }
}

const toggleValidator = (v) => {
  if (!v.configured) return
  const idx = selectedValidators.value.indexOf(v.index)
  if (idx >= 0) {
    selectedValidators.value.splice(idx, 1)
  } else {
    selectedValidators.value.push(v.index)
  }
}

onMounted(() => {
  addLog('Step3 simulation run initialized')
  if (props.simulationId) {
    fetchScheduledEvents()
    fetchValidators()
    doStartSimulation()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.simulation-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0a0a0f;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
  overflow: hidden;
}

/* --- Control Bar --- */
.control-bar {
  background: rgba(10, 10, 15, 0.95);
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  z-index: 10;
  height: 64px;
  backdrop-filter: blur(12px);
}

.status-group {
  display: flex;
  gap: 12px;
}

/* Platform Status Cards */
.platform-status {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  opacity: 0.7;
  transition: all 0.3s;
  min-width: 140px;
  position: relative;
  cursor: pointer;
}

.platform-status.active {
  opacity: 1;
  border-color: #638cff;
  background: rgba(99, 140, 255, 0.06);
}

.platform-status.completed {
  opacity: 1;
  border-color: #34d399;
  background: rgba(52, 211, 153, 0.06);
}

/* Actions Tooltip */
.actions-tooltip {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-top: 8px;
  padding: 10px 14px;
  background: #000;
  color: #FFF;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s ease;
  z-index: 100;
  min-width: 180px;
  pointer-events: none;
}

.actions-tooltip::before {
  content: '';
  position: absolute;
  top: -6px;
  left: 50%;
  transform: translateX(-50%);
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-bottom: 6px solid #000;
}

.platform-status:hover.actions-tooltip {
  opacity: 1;
  visibility: visible;
}

.tooltip-title {
  font-size: 10px;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 8px;
}

.tooltip-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tooltip-action {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
  color: #FFF;
  letter-spacing: 0.03em;
}

.platform-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.platform-name {
  font-size: 11px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.87);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.platform-status.twitter.platform-icon { color: rgba(255, 255, 255, 0.87); }
.platform-status.reddit.platform-icon { color: rgba(255, 255, 255, 0.87); }

.platform-stats {
  display: flex;
  gap: 10px;
}

.stat {
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.stat-label {
  font-size: 8px;
  color: rgba(255, 255, 255, 0.35);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.87);
}

.stat-total,.stat-unit {
  font-size: 9px;
  color: rgba(255, 255, 255, 0.35);
  font-weight: 400;
}

.status-badge {
  margin-left: auto;
  color: #34d399;
  display: flex;
  align-items: center;
}

/* Action Button */
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 600;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.action-btn.primary {
  background: #638cff;
  color: #FFFFFF;
}

.action-btn.primary:hover:not(:disabled) {
  background: #7aa0ff;
}

.action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* --- Main Content Area --- */
.main-content-area {
  flex: 1;
  overflow-y: auto;
  position: relative;
  background: #0a0a0f;
}

/* Timeline Header */
.timeline-header {
  position: sticky;
  top: 0;
  background: rgba(10, 10, 15, 0.9);
  backdrop-filter: blur(8px);
  padding: 12px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  z-index: 5;
  display: flex;
  justify-content: center;
}

.timeline-stats {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.04);
  padding: 4px 12px;
  border-radius: 20px;
}

.total-count {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.87);
}

.platform-breakdown {
  display: flex;
  align-items: center;
  gap: 8px;
}

.breakdown-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.breakdown-divider { color: rgba(255, 255, 255, 0.15); }
.breakdown-item.twitter { color: rgba(255, 255, 255, 0.87); }
.breakdown-item.reddit { color: rgba(255, 255, 255, 0.87); }

/* --- Timeline Feed --- */
.timeline-feed {
  padding: 24px 0;
  position: relative;
  min-height: 100%;
  max-width: 900px;
  margin: 0 auto;
}

.timeline-axis {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 1px;
  background: rgba(255, 255, 255, 0.06);
  transform: translateX(-50%);
}

.timeline-item {
  display: flex;
  justify-content: center;
  margin-bottom: 32px;
  position: relative;
  width: 100%;
}

.timeline-marker {
  position: absolute;
  left: 50%;
  top: 24px;
  width: 10px;
  height: 10px;
  background: #0a0a0f;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  transform: translateX(-50%);
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
}

.marker-dot {
  width: 4px;
  height: 4px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 50%;
}

.timeline-item.twitter.marker-dot { background: #638cff; }
.timeline-item.reddit.marker-dot { background: #638cff; }
.timeline-item.twitter.timeline-marker { border-color: #638cff; }
.timeline-item.reddit.timeline-marker { border-color: #638cff; }

/* Card Layout */
.timeline-card {
  width: calc(100% - 48px);
  background: rgba(255, 255, 255, 0.03);
  border-radius: 2px;
  padding: 16px 20px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 2px 10px rgba(0,0,0,0.15);
  position: relative;
  transition: all 0.2s;
}

.timeline-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.25);
  border-color: rgba(255, 255, 255, 0.1);
}

/* Left side (Twitter) */
.timeline-item.twitter {
  justify-content: flex-start;
  padding-right: 50%;
}
.timeline-item.twitter.timeline-card {
  margin-left: auto;
  margin-right: 32px; /* Gap from axis */
}

/* Right side (Reddit) */
.timeline-item.reddit {
  justify-content: flex-end;
  padding-left: 50%;
}
.timeline-item.reddit.timeline-card {
  margin-right: auto;
  margin-left: 32px; /* Gap from axis */
}

/* Card Content Styles */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.agent-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar-placeholder {
  width: 24px;
  height: 24px;
  background: #638cff;
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.agent-name {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.87);
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.platform-indicator {
  color: rgba(255, 255, 255, 0.35);
  display: flex;
  align-items: center;
}

.action-badge {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 2px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: 1px solid transparent;
}

/* Monochromatic Badges */
.badge-post { background: rgba(99, 140, 255, 0.1); color: #638cff; border-color: rgba(99, 140, 255, 0.2); }
.badge-comment { background: rgba(255, 255, 255, 0.06); color: rgba(255, 255, 255, 0.55); border-color: rgba(255, 255, 255, 0.1); }
.badge-action { background: transparent; color: rgba(255, 255, 255, 0.45); border: 1px solid rgba(255, 255, 255, 0.1); }
.badge-meta { background: rgba(255, 255, 255, 0.03); color: rgba(255, 255, 255, 0.35); border: 1px dashed rgba(255, 255, 255, 0.1); }
.badge-idle { opacity: 0.5; }

.content-text {
  font-size: 13px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.65);
  margin-bottom: 10px;
}

.content-text.main-text {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.87);
}

/* Info Blocks (Quote, Repost, etc) */
.quoted-block,.repost-content {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 10px 12px;
  border-radius: 2px;
  margin-top: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
}

.quote-header,.repost-info,.like-info,.search-info,.follow-info,.vote-info,.idle-info,.comment-context {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.icon-small {
  color: rgba(255, 255, 255, 0.3);
}
.icon-small.filled {
  color: rgba(255, 255, 255, 0.3);
}

.search-query {
  font-family: 'JetBrains Mono', monospace;
  background: rgba(255, 255, 255, 0.06);
  padding: 0 4px;
  border-radius: 2px;
}

.card-footer {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.25);
  font-family: 'JetBrains Mono', monospace;
}

/* Waiting State */
.waiting-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: rgba(255, 255, 255, 0.35);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.pulse-ring {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.1);
  animation: ripple 2s infinite;
}

@keyframes ripple {
  0% { transform: scale(0.8); opacity: 1; border-color: rgba(255, 255, 255, 0.2); }
  100% { transform: scale(2.5); opacity: 0; border-color: rgba(255, 255, 255, 0.05); }
}

/* Animation */
.timeline-item-enter-active,
.timeline-item-leave-active {
  transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.timeline-item-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.timeline-item-leave-to {
  opacity: 0;
}

/* Logs */
.system-logs {
  background: rgba(0, 0, 0, 0.4);
  color: rgba(255, 255, 255, 0.65);
  padding: 16px;
  font-family: 'JetBrains Mono', monospace;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
  overflow: hidden;
  min-width: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 8px;
  margin-bottom: 8px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.35);
  min-width: 0;
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 120px;
  overflow-y: auto;
  padding-right: 4px;
}

.log-content::-webkit-scrollbar { width: 4px; }
.log-content::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 2px; }

.log-line {
  font-size: 11px;
  display: flex;
  gap: 12px;
  line-height: 1.5;
  min-width: 0;
}

.log-time { color: rgba(255, 255, 255, 0.25); min-width: 75px; flex-shrink: 0; }
.log-msg { color: rgba(255, 255, 255, 0.55); word-break: break-word; overflow-wrap: anywhere; min-width: 0; }
.mono { font-family: 'JetBrains Mono', monospace; }

/* Loading spinner for button */
.loading-spinner-small {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFF;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 6px;
}

/* ── Geopolitical Event Timeline Cards ── */
.timeline-item.geopolitical {
  justify-content: center;
  padding: 0 60px;
}
.timeline-item.geopolitical .timeline-marker { border-color: #EF4444; }
.timeline-item.geopolitical .marker-dot { background: #EF4444; }

.geo-event-card {
  width: 100%;
  background: rgba(251, 191, 36, 0.06);
  border: 1px solid rgba(251, 191, 36, 0.3);
  border-left: 3px solid rgba(251, 191, 36, 0.5);
  border-radius: 2px;
  padding: 14px 18px;
}
.geo-event-card.severity-critical { border-color: rgba(248, 113, 113, 0.4); background: rgba(248, 113, 113, 0.06); }
.geo-event-card.severity-high { border-color: rgba(249, 115, 22, 0.4); background: rgba(249, 115, 22, 0.06); }
.geo-event-card.severity-medium { border-color: rgba(251, 191, 36, 0.3); background: rgba(251, 191, 36, 0.06); }
.geo-event-card.severity-low { border-color: rgba(234, 179, 8, 0.3); background: rgba(234, 179, 8, 0.04); }

.geo-event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.geo-event-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 9px;
  font-weight: 700;
  color: #fbbf24;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.geo-event-badge svg { color: #fbbf24; }
.severity-critical .geo-event-badge { color: #f87171; }
.severity-critical .geo-event-badge svg { color: #f87171; }

.geo-severity-tag {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 2px;
  letter-spacing: 0.08em;
}
.sev-critical { background: rgba(248, 113, 113, 0.15); color: #f87171; }
.sev-high { background: rgba(249, 115, 22, 0.15); color: #fb923c; }
.sev-medium { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
.sev-low { background: rgba(234, 179, 8, 0.12); color: #eab308; }

.geo-event-body { margin-bottom: 8px; }
.geo-event-category {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #fbbf24;
  margin-bottom: 4px;
}
.geo-event-title {
  font-size: 14px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.87);
  margin-bottom: 6px;
}
.geo-event-desc {
  font-size: 12px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.55);
  margin: 0;
}
.geo-event-meta {
  display: flex;
  gap: 14px;
  margin-top: 8px;
  font-size: 11px;
}
.geo-impact {
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}
.geo-impact.negative { color: #f87171; }
.geo-impact.positive { color: #34d399; }
.geo-affected { color: rgba(255, 255, 255, 0.4); }

/* ── Consensus Config Panel ─────────────────────── */
.consensus-config-panel {
  padding: 14px 16px;
  margin: 8px 0;
  border: 1px solid #E5E7EB;
  border-radius: 10px;
  background: #FAFBFC;
}

.consensus-config-panel.panel-ready {
  border-color: #0d6f70;
  background: rgba(13, 111, 112, 0.02);
}

.consensus-section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 10px;
}

.consensus-summary {
  margin-top: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  color: #638cff;
  font-weight: 500;
  padding: 6px 10px;
  background: rgba(99, 140, 255, 0.08);
  border-radius: 6px;
}

.consensus-toggle-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.consensus-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.consensus-toggle input {
  display: none;
}

.toggle-track {
  width: 36px;
  height: 20px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.12);
  position: relative;
  transition: background 0.2s ease;
  flex-shrink: 0;
}

.consensus-toggle input:checked + .toggle-track {
  background: #638cff;
}

.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.7);
  transition: transform 0.2s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.consensus-toggle input:checked + .toggle-track .toggle-thumb {
  transform: translateX(16px);
}

.toggle-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: rgba(255, 255, 255, 0.87);
}

.consensus-hint {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.35);
}

.consensus-hint.active {
  color: #638cff;
}

.consensus-single-warn {
  font-size: 0.68rem;
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 6px;
  padding: 6px 10px;
  margin-top: 8px;
}

.validator-selector {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.validator-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
  transition: all 0.18s ease;
  user-select: none;
}

.validator-chip:hover:not(.disabled) {
  border-color: rgba(99, 140, 255, 0.3);
  background: rgba(99, 140, 255, 0.06);
}

.validator-chip.selected {
  border-color: rgba(99, 140, 255, 0.4);
  background: rgba(99, 140, 255, 0.08);
}

.validator-chip.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.chip-index {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  padding: 2px 5px;
}

.validator-chip.selected .chip-index {
  color: #638cff;
  background: rgba(99, 140, 255, 0.15);
}

.chip-model {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.74rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.87);
}

.chip-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.64rem;
  color: #9CA3AF;
}

.chip-check {
  color: #638cff;
  display: flex;
  align-items: center;
}

/* Consensus panel transition */
.consensus-panel-enter-active,
.consensus-panel-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.consensus-panel-enter-from,
.consensus-panel-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.consensus-panel-enter-to,
.consensus-panel-leave-from {
  opacity: 1;
  max-height: 200px;
}
</style>