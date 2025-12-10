/**
 * Reusable form input components for consistent styling across the application.
 */

import { Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';

/**
 * Text input with label
 */
export function FormInput({
    label,
    name,
    type = 'text',
    value,
    onChange,
    required = false,
    placeholder,
    className = '',
    ...props
}) {
    return (
        <div className={className}>
            {label && (
                <label htmlFor={name} className="block text-xs font-medium text-slate-400 mb-1">
                    {label} {required && '*'}
                </label>
            )}
            <input
                type={type}
                id={name}
                name={name}
                value={value}
                onChange={onChange}
                placeholder={placeholder}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
                required={required}
                {...props}
            />
        </div>
    );
}

/**
 * Password input with show/hide toggle
 */
export function PasswordInput({
    label,
    name,
    value,
    onChange,
    required = false,
    showPassword: externalShowPassword,
    onToggleShow,
    className = '',
    ...props
}) {
    const [internalShowPassword, setInternalShowPassword] = useState(false);

    // Use external control if provided, otherwise use internal state
    const showPassword = externalShowPassword !== undefined ? externalShowPassword : internalShowPassword;
    const toggleShow = onToggleShow || (() => setInternalShowPassword(!internalShowPassword));

    return (
        <div className={className}>
            {label && (
                <label htmlFor={name} className="block text-xs font-medium text-slate-400 mb-1">
                    {label} {required && '*'}
                </label>
            )}
            <div className="relative">
                <input
                    type={showPassword ? 'text' : 'password'}
                    id={name}
                    name={name}
                    value={value}
                    onChange={onChange}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
                    required={required}
                    {...props}
                />
                <button
                    type="button"
                    onClick={toggleShow}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-300"
                    tabIndex={-1}
                >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
            </div>
        </div>
    );
}

/**
 * Select dropdown with label
 */
export function FormSelect({
    label,
    name,
    value,
    onChange,
    options,
    required = false,
    placeholder = 'Select...',
    className = '',
    ...props
}) {
    return (
        <div className={className}>
            {label && (
                <label htmlFor={name} className="block text-xs font-medium text-slate-400 mb-1">
                    {label} {required && '*'}
                </label>
            )}
            <select
                id={name}
                name={name}
                value={value}
                onChange={onChange}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                required={required}
                {...props}
            >
                <option value="">{placeholder}</option>
                {options.map(option => (
                    <option key={option.value || option} value={option.value || option}>
                        {option.label || option}
                    </option>
                ))}
            </select>
        </div>
    );
}

/**
 * Checkbox input with label
 */
export function FormCheckbox({
    label,
    name,
    checked,
    onChange,
    required = false,
    className = '',
    ...props
}) {
    return (
        <label className={`flex items-start gap-3 cursor-pointer ${className}`}>
            <input
                type="checkbox"
                name={name}
                checked={checked}
                onChange={onChange}
                className="mt-1 w-4 h-4 rounded border-slate-600 bg-slate-900 text-green-500 focus:ring-green-500"
                required={required}
                {...props}
            />
            <span className="text-sm text-slate-300">{label}</span>
        </label>
    );
}

/**
 * Form section with heading
 */
export function FormSection({ title, children, className = '' }) {
    return (
        <div className={`space-y-3 ${className}`}>
            <h3 className="text-sm font-medium text-slate-300 border-b border-slate-700 pb-2">
                {title}
            </h3>
            {children}
        </div>
    );
}
