/**
 * useFormValidation Hook
 *
 * Provides form validation with real-time feedback and error handling.
 * Supports common validation rules and custom validators.
 */

import { useState, useCallback, useMemo } from 'react';

/**
 * Built-in validation rules
 */
export const validators = {
  /**
   * Check if value is not empty
   */
  required: (message = 'This field is required') => (value) => {
    if (value === null || value === undefined) return message;
    if (typeof value === 'string' && value.trim() === '') return message;
    if (Array.isArray(value) && value.length === 0) return message;
    return null;
  },

  /**
   * Check minimum length
   */
  minLength: (min, message) => (value) => {
    if (!value) return null;
    const msg = message || `Must be at least ${min} characters`;
    return value.length < min ? msg : null;
  },

  /**
   * Check maximum length
   */
  maxLength: (max, message) => (value) => {
    if (!value) return null;
    const msg = message || `Must be no more than ${max} characters`;
    return value.length > max ? msg : null;
  },

  /**
   * Check if value matches email format
   */
  email: (message = 'Please enter a valid email address') => (value) => {
    if (!value) return null;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(value) ? null : message;
  },

  /**
   * Check if value matches URL format
   */
  url: (message = 'Please enter a valid URL') => (value) => {
    if (!value) return null;
    try {
      new URL(value);
      return null;
    } catch {
      return message;
    }
  },

  /**
   * Check if value is a number
   */
  number: (message = 'Please enter a valid number') => (value) => {
    if (!value && value !== 0) return null;
    return isNaN(Number(value)) ? message : null;
  },

  /**
   * Check minimum value for numbers
   */
  min: (minValue, message) => (value) => {
    if (value === '' || value === null || value === undefined) return null;
    const msg = message || `Must be at least ${minValue}`;
    return Number(value) < minValue ? msg : null;
  },

  /**
   * Check maximum value for numbers
   */
  max: (maxValue, message) => (value) => {
    if (value === '' || value === null || value === undefined) return null;
    const msg = message || `Must be no more than ${maxValue}`;
    return Number(value) > maxValue ? msg : null;
  },

  /**
   * Check if value matches a regex pattern
   */
  pattern: (regex, message = 'Invalid format') => (value) => {
    if (!value) return null;
    return regex.test(value) ? null : message;
  },

  /**
   * Check if value matches another field
   */
  matches: (fieldName, message) => (value, allValues) => {
    if (!value) return null;
    const msg = message || `Must match ${fieldName}`;
    return value === allValues[fieldName] ? null : msg;
  },

  /**
   * Password strength validation
   */
  password: (options = {}) => (value) => {
    if (!value) return null;

    const {
      minLength = 8,
      requireUppercase = true,
      requireLowercase = true,
      requireNumbers = true,
      requireSpecial = false,
    } = options;

    const errors = [];

    if (value.length < minLength) {
      errors.push(`at least ${minLength} characters`);
    }
    if (requireUppercase && !/[A-Z]/.test(value)) {
      errors.push('an uppercase letter');
    }
    if (requireLowercase && !/[a-z]/.test(value)) {
      errors.push('a lowercase letter');
    }
    if (requireNumbers && !/[0-9]/.test(value)) {
      errors.push('a number');
    }
    if (requireSpecial && !/[!@#$%^&*(),.?":{}|<>]/.test(value)) {
      errors.push('a special character');
    }

    if (errors.length > 0) {
      return `Password must contain ${errors.join(', ')}`;
    }
    return null;
  },

  /**
   * License key format validation
   */
  licenseKey: (message = 'Invalid license key format') => (value) => {
    if (!value) return null;
    // Format: XXXX-XXXX-XXXX-XXXX (alphanumeric with hyphens)
    const licenseRegex = /^[A-Z0-9]{4,}-[A-Z0-9]{4,}-[A-Z0-9]{4,}(-[A-Z0-9]{4,})?$/i;
    return licenseRegex.test(value) ? null : message;
  },
};

/**
 * useFormValidation Hook
 *
 * @param {Object} initialValues - Initial form values
 * @param {Object} validationSchema - Validation schema with field names as keys
 * @param {Object} options - Additional options
 * @returns {Object} Form state and handlers
 *
 * @example
 * const { values, errors, handleChange, handleBlur, handleSubmit, isValid } = useFormValidation(
 *   { email: '', password: '' },
 *   {
 *     email: [validators.required(), validators.email()],
 *     password: [validators.required(), validators.minLength(8)],
 *   }
 * );
 */
export function useFormValidation(initialValues, validationSchema, options = {}) {
  const { validateOnChange = true, validateOnBlur = true } = options;

  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  /**
   * Validate a single field
   */
  const validateField = useCallback((name, value, allValues = values) => {
    const fieldValidators = validationSchema[name];
    if (!fieldValidators) return null;

    const validators = Array.isArray(fieldValidators)
      ? fieldValidators
      : [fieldValidators];

    for (const validator of validators) {
      const error = validator(value, allValues);
      if (error) return error;
    }
    return null;
  }, [validationSchema, values]);

  /**
   * Validate all fields
   */
  const validateAll = useCallback(() => {
    const newErrors = {};
    let hasErrors = false;

    for (const name of Object.keys(validationSchema)) {
      const error = validateField(name, values[name], values);
      if (error) {
        newErrors[name] = error;
        hasErrors = true;
      }
    }

    setErrors(newErrors);
    return !hasErrors;
  }, [validationSchema, values, validateField]);

  /**
   * Handle input change
   */
  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    const newValue = type === 'checkbox' ? checked : value;

    setValues(prev => {
      const newValues = { ...prev, [name]: newValue };

      if (validateOnChange && touched[name]) {
        const error = validateField(name, newValue, newValues);
        setErrors(prevErrors => ({
          ...prevErrors,
          [name]: error,
        }));
      }

      return newValues;
    });
  }, [touched, validateField, validateOnChange]);

  /**
   * Set a specific field value programmatically
   */
  const setValue = useCallback((name, value) => {
    setValues(prev => ({ ...prev, [name]: value }));
    if (validateOnChange && touched[name]) {
      const error = validateField(name, value);
      setErrors(prevErrors => ({ ...prevErrors, [name]: error }));
    }
  }, [touched, validateField, validateOnChange]);

  /**
   * Handle input blur
   */
  const handleBlur = useCallback((e) => {
    const { name, value } = e.target;

    setTouched(prev => ({ ...prev, [name]: true }));

    if (validateOnBlur) {
      const error = validateField(name, value);
      setErrors(prevErrors => ({ ...prevErrors, [name]: error }));
    }
  }, [validateField, validateOnBlur]);

  /**
   * Handle form submission
   */
  const handleSubmit = useCallback((onSubmit) => async (e) => {
    e?.preventDefault();

    // Mark all fields as touched
    const allTouched = {};
    for (const name of Object.keys(validationSchema)) {
      allTouched[name] = true;
    }
    setTouched(allTouched);

    // Validate all fields
    const isValid = validateAll();
    if (!isValid) return;

    // Submit
    setIsSubmitting(true);
    try {
      await onSubmit(values);
    } finally {
      setIsSubmitting(false);
    }
  }, [values, validateAll, validationSchema]);

  /**
   * Reset form to initial values
   */
  const reset = useCallback((newInitialValues) => {
    setValues(newInitialValues || initialValues);
    setErrors({});
    setTouched({});
    setIsSubmitting(false);
  }, [initialValues]);

  /**
   * Check if a field has an error
   */
  const hasError = useCallback((name) => {
    return touched[name] && !!errors[name];
  }, [touched, errors]);

  /**
   * Get error message for a field
   */
  const getError = useCallback((name) => {
    return touched[name] ? errors[name] : null;
  }, [touched, errors]);

  /**
   * Check if form is valid
   */
  const isValid = useMemo(() => {
    return Object.keys(validationSchema).every(name => !validateField(name, values[name], values));
  }, [validationSchema, values, validateField]);

  /**
   * Check if form has been modified
   */
  const isDirty = useMemo(() => {
    return Object.keys(initialValues).some(name => values[name] !== initialValues[name]);
  }, [initialValues, values]);

  return {
    values,
    errors,
    touched,
    isSubmitting,
    isValid,
    isDirty,
    handleChange,
    handleBlur,
    handleSubmit,
    setValue,
    setValues,
    setErrors,
    reset,
    hasError,
    getError,
    validateField,
    validateAll,
  };
}

export default useFormValidation;
