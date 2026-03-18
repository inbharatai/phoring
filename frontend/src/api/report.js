import service, { requestWithRetry } from './index'

/**
 * Get available AI validators for consensus configuration
 */
export const getValidators = () => {
  return service.get('/api/report/validators')
}

/**
 * startreportgenerate
 * @param {Object} data - { simulation_id, force_regenerate?, consensus_config? }
 */
export const generateReport = (data) => {
  return requestWithRetry(() => service.post('/api/report/generate', data), 3, 1000)
}

/**
 * Getreportgeneratestatus
 * @param {string} reportId
 */
export const getReportStatus = (reportId) => {
  return service.get(`/api/report/generate/status`, { params: { report_id: reportId } })
}

/**
 * Get Agent log()
 * @param {string} reportId
 * @param {number} fromLine - Start line for retrieval
 */
export const getAgentLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/agent-log`, { params: { from_line: fromLine } })
}

/**
 * Get log()
 * @param {string} reportId
 * @param {number} fromLine - Start line for retrieval
 */
export const getConsoleLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/console-log`, { params: { from_line: fromLine } })
}

/**
 * Getreport 
 * @param {string} reportId
 */
export const getReport = (reportId) => {
  return service.get(`/api/report/${reportId}`)
}

/**
 * Report Agent 
 * @param {Object} data - { simulation_id, message, chat_history? }
 */
export const chatWithReport = (data) => {
  return requestWithRetry(() => service.post('/api/report/chat', data), 3, 1000)
}
