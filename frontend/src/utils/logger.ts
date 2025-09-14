// Browser-compatible logging solution
interface LogEntry {
  timestamp: string;
  level: string;
  category: string;
  message: string;
  data?: any;
  stack?: string;
}

class BrowserLogger {
  private logLevel: number = 2; // 0=debug, 1=info, 2=warn, 3=error
  
  constructor() {
    // Set log level based on environment
    if (process.env.NODE_ENV === 'development') {
      this.logLevel = 1; // Show info and above in development
    }
  }

  private shouldLog(level: number): boolean {
    return level >= this.logLevel;
  }

  private createLogEntry(level: string, category: string, message: string, ...meta: any[]): LogEntry {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      category,
      message
    };

    if (meta.length > 0) {
      entry.data = meta.length === 1 ? meta[0] : meta;
      
      // Extract stack trace if error is passed
      const error = meta.find(m => m instanceof Error);
      if (error) {
        entry.stack = error.stack;
      }
    }

    return entry;
  }

  private logToConsole(entry: LogEntry): void {
    const consoleMessage = `${entry.timestamp} [${entry.level.toUpperCase()}] [${entry.category}] ${entry.message}`;
    
    switch (entry.level) {
      case 'debug':
        console.debug(consoleMessage, entry.data);
        break;
      case 'info':
        console.info(consoleMessage, entry.data);
        break;
      case 'warn':
        console.warn(consoleMessage, entry.data);
        break;
      case 'error':
        console.error(consoleMessage, entry.data);
        if (entry.stack) console.error(entry.stack);
        break;
    }
  }

  private storeLog(entry: LogEntry): void {
    try {
      const logs = JSON.parse(localStorage.getItem('ftransport-logs') || '[]');
      logs.push(entry);

      // Keep only last 1000 log entries
      if (logs.length > 1000) {
        logs.splice(0, logs.length - 1000);
      }

      localStorage.setItem('ftransport-logs', JSON.stringify(logs));
    } catch (error) {
      console.error('Failed to store log to localStorage:', error);
    }
  }

  private log(level: string, levelNum: number, category: string, message: string, ...meta: any[]): void {
    if (!this.shouldLog(levelNum)) return;

    const entry = this.createLogEntry(level, category, message, ...meta);
    
    // Always log to console
    this.logToConsole(entry);
    
    // Store in localStorage for debugging
    this.storeLog(entry);
  }

  debug(category: string, message: string, ...meta: any[]): void {
    this.log('debug', 0, category, message, ...meta);
  }

  info(category: string, message: string, ...meta: any[]): void {
    this.log('info', 1, category, message, ...meta);
  }

  warn(category: string, message: string, ...meta: any[]): void {
    this.log('warn', 2, category, message, ...meta);
  }

  error(category: string, message: string, ...meta: any[]): void {
    this.log('error', 3, category, message, ...meta);
  }
}

const logger = new BrowserLogger();

// Export specific loggers for different components
export const uiLogger = {
  info: (message: string, ...meta: any[]) => logger.info('UI', message, ...meta),
  warn: (message: string, ...meta: any[]) => logger.warn('UI', message, ...meta),
  error: (message: string, ...meta: any[]) => logger.error('UI', message, ...meta),
  debug: (message: string, ...meta: any[]) => logger.debug('UI', message, ...meta)
};

export const transferLogger = {
  info: (message: string, ...meta: any[]) => logger.info('TRANSFER', message, ...meta),
  warn: (message: string, ...meta: any[]) => logger.warn('TRANSFER', message, ...meta),
  error: (message: string, ...meta: any[]) => logger.error('TRANSFER', message, ...meta),
  debug: (message: string, ...meta: any[]) => logger.debug('TRANSFER', message, ...meta)
};

export const apiLogger = {
  info: (message: string, ...meta: any[]) => logger.info('API', message, ...meta),
  warn: (message: string, ...meta: any[]) => logger.warn('API', message, ...meta),
  error: (message: string, ...meta: any[]) => logger.error('API', message, ...meta),
  debug: (message: string, ...meta: any[]) => logger.debug('API', message, ...meta)
};

export const websocketLogger = {
  info: (message: string, ...meta: any[]) => logger.info('WEBSOCKET', message, ...meta),
  warn: (message: string, ...meta: any[]) => logger.warn('WEBSOCKET', message, ...meta),
  error: (message: string, ...meta: any[]) => logger.error('WEBSOCKET', message, ...meta),
  debug: (message: string, ...meta: any[]) => logger.debug('WEBSOCKET', message, ...meta)
};

// Function to retrieve logs for debugging
export const getLogs = (): any[] => {
  try {
    return JSON.parse(localStorage.getItem('ftransport-logs') || '[]');
  } catch (error) {
    console.error('Failed to retrieve logs:', error);
    return [];
  }
};

// Function to clear logs
export const clearLogs = (): void => {
  try {
    localStorage.removeItem('ftransport-logs');
    logger.info('SYSTEM', 'Logs cleared from browser storage');
  } catch (error) {
    console.error('Failed to clear logs:', error);
  }
};

// Function to export logs as a file
export const exportLogs = (): void => {
  try {
    const logs = getLogs();
    const logText = logs.map(log => 
      `${log.timestamp} [${log.level.toUpperCase()}] ${log.message}${log.stack ? '\n' + log.stack : ''}`
    ).join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ftransport-logs-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    logger.info('SYSTEM', 'Logs exported to file');
  } catch (error) {
    console.error('Failed to export logs:', error);
  }
};

export default logger;