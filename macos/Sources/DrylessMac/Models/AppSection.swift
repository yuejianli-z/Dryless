import DrylessCore
import Foundation

enum AppSection: String, CaseIterable, Identifiable {
    case monitor
    case stats
    case settings

    var id: String { rawValue }

    var systemImage: String {
        switch self {
        case .monitor: return "eye"
        case .stats: return "chart.bar.xaxis"
        case .settings: return "slider.horizontal.3"
        }
    }

    func title(language: AppLanguage) -> String {
        switch (self, language) {
        case (.monitor, .en): return "Monitor"
        case (.stats, .en): return "Stats"
        case (.settings, .en): return "Settings"
        case (.monitor, .zh): return "监控"
        case (.stats, .zh): return "统计"
        case (.settings, .zh): return "设置"
        }
    }

    func detail(language: AppLanguage) -> String {
        switch (self, language) {
        case (.monitor, .en): return "Live blink detection"
        case (.stats, .en): return "Local history"
        case (.settings, .en): return "Sensitivity and alerts"
        case (.monitor, .zh): return "实时眨眼检测"
        case (.stats, .zh): return "本地历史记录"
        case (.settings, .zh): return "灵敏度与提醒"
        }
    }
}
