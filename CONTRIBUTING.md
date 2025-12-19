# Contributing to D-Farms Trading Bot

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

1. **Fork the repository**
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/D-Farms-Trading-Bot.git
   cd D-Farms-Trading-Bot
   ```
3. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 📝 Development Guidelines

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and modular

### Testing

- Test your changes locally using Docker
- Verify the dashboard displays correctly
- Check logs for errors: `logs/trade_executor.log`, `logs/market_scanner.log`

### Commit Messages

Use clear, descriptive commit messages:

```
feat: Add new technical indicator (RSI divergence)
fix: Correct timezone handling in orchestrator
docs: Update OCI setup guide
refactor: Simplify market scanner logic
```

## 🔧 Areas for Contribution

### High Priority
- **Backtesting Framework**: Historical strategy validation
- **Additional Strategies**: Mean reversion, breakout patterns
- **Enhanced Risk Management**: Dynamic position sizing
- **Performance Metrics**: Sharpe ratio, max drawdown tracking

### Medium Priority
- **More Indicators**: MACD, Bollinger Bands, Volume Profile
- **Crypto Integration**: Direct exchange API support
- **Alert Customization**: Configurable notification rules
- **Dashboard Improvements**: Mobile responsiveness, dark mode

### Low Priority
- **Unit Tests**: Increase test coverage
- **Documentation**: Video tutorials, strategy guides
- **UI/UX**: Dashboard themes, custom layouts

## 🐛 Reporting Bugs

When reporting bugs, please include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Exact steps to trigger the bug
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: OS, Docker version, Python version
6. **Logs**: Relevant log excerpts

## 💡 Suggesting Features

Feature requests are welcome! Please:

1. Check if the feature already exists or is planned
2. Describe the use case and benefits
3. Provide examples or mockups if applicable
4. Consider implementation complexity

## 🔒 Security

**Do NOT commit**:
- API keys or tokens
- `.env` files
- OCI credentials (`.oci/`, `*.pem`)
- Terraform state files (`*.tfstate`)
- Database files (`*.db`)

These are already in `.gitignore`, but double-check before committing.

## 📋 Pull Request Process

1. **Update Documentation**: If you change functionality, update relevant docs
2. **Test Thoroughly**: Ensure your changes don't break existing features
3. **Update CHANGELOG**: Add your changes to the unreleased section
4. **Submit PR**: Provide a clear description of changes
5. **Respond to Feedback**: Address review comments promptly

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Code follows project style guidelines
- [ ] Documentation updated
- [ ] No sensitive data committed
- [ ] Tested locally
```

## 🤝 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

## 📞 Questions?

If you have questions, feel free to:
- Open an issue with the `question` label
- Reach out to [@KrishnaVidhul](https://github.com/KrishnaVidhul)

Thank you for contributing! 🎉
