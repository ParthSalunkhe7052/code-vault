import { useState, useCallback, useMemo, ChangeEvent } from 'react';

export type ValidatorFn = (value: any, allValues: any) => string | null;

export interface ValidationSchema {
  [key: string]: ValidatorFn | ValidatorFn[];
}

export interface FormOptions {
  validateOnChange?: boolean;
  validateOnBlur?: boolean;
}

/**
 * Built-in validation rules
 */
export const validators = {
  required: (message = 'This field is required'): ValidatorFn => (value) => {
    if (value === null || value === undefined) return message;
    if (typeof value === 'string' && value.trim() === '') return message;
    if (Array.isArray(value) && value.length === 0) return message;
    return null;
  },

  minLength: (min: number, message?: string): ValidatorFn => (value) => {
    if (!value) return null;
    const msg = message || `Must be at least ${min} characters`;
    return value.length < min ? msg : null;
  },

  maxLength: (max: number, message?: string): ValidatorFn => (value) => {
    if (!value) return null;
    const msg = message || `Must be no more than ${max} characters`;
    return value.length > max ? msg : null;
  },

  email: (message = 'Please enter a valid email address'): ValidatorFn => (value) => {
    if (!value) return null;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(value) ? null : message;
  },

  url: (message = 'Please enter a valid URL'): ValidatorFn => (value) => {
    if (!value) return null;
    try {
      new URL(value);
      return null;
    } catch {
      return message;
    }
  },

  number: (message = 'Please enter a valid number'): ValidatorFn => (value) => {
    if (!value && value !== 0) return null;
    return isNaN(Number(value)) ? message : null;
  },

  min: (minValue: number, message?: string): ValidatorFn => (value) => {
    if (value === '' || value === null || value === undefined) return null;
    const msg = message || `Must be at least ${minValue}`;
    return Number(value) < minValue ? msg : null;
  },

  max: (maxValue: number, message?: string): ValidatorFn => (value) => {
    if (value === '' || value === null || value === undefined) return null;
    const msg = message || `Must be no more than ${maxValue}`;
    return Number(value) > maxValue ? msg : null;
  },

  pattern: (regex: RegExp, message = 'Invalid format'): ValidatorFn => (value) => {
    if (!value) return null;
    return regex.test(value) ? null : message;
  },

  matches: (fieldName: string, message?: string): ValidatorFn => (value, allValues) => {
    if (!value) return null;
    const msg = message || `Must match ${fieldName}`;
    return value === allValues[fieldName] ? null : msg;
  },

  password: (options: {
    minLength?: number;
    requireUppercase?: boolean;
    requireLowercase?: boolean;
    requireNumbers?: boolean;
    requireSpecial?: boolean;
  } = {}): ValidatorFn => (value) => {
    if (!value) return null;

    const {
      minLength = 8,
      requireUppercase = true,
      requireLowercase = true,
      requireNumbers = true,
      requireSpecial = false,
    } = options;

    const errors: string[] = [];

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

  licenseKey: (message = 'Invalid license key format'): ValidatorFn => (value) => {
    if (!value) return null;
    const licenseRegex = /^[A-Z0-9]{4,}-[A-Z0-9]{4,}-[A-Z0-9]{4,}(-[A-Z0-9]{4,})?$/i;
    return licenseRegex.test(value) ? null : message;
  },
};

/**
 * useFormValidation Hook
 */
export function useFormValidation<T extends Record<string, any>>(
  initialValues: T,
  validationSchema: ValidationSchema,
  options: FormOptions = {}
) {
  const { validateOnChange = true, validateOnBlur = true } = options;

  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<Record<string, string | null>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  /**
   * Validate a single field
   */
  const validateField = useCallback((name: string, value: any, allValues: T = values) => {
    const fieldRules = validationSchema[name];
    if (!fieldRules) return null;

    const rules = Array.isArray(fieldRules) ? fieldRules : [fieldRules];

    for (const rule of rules) {
      const error = rule(value, allValues);
      if (error) return error;
    }
    return null;
  }, [validationSchema, values]);

  /**
   * Validate all fields
   */
  const validateAll = useCallback(() => {
    const newErrors: Record<string, string | null> = {};
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
  const handleChange = useCallback((e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    const newValue = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value;

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
  const setValue = useCallback((name: keyof T, value: any) => {
    setValues(prev => {
      const newValues = { ...prev, [name as string]: value };
      if (validateOnChange && touched[name as string]) {
        const error = validateField(name as string, value, newValues);
        setErrors(prevErrors => ({ ...prevErrors, [name as string]: error }));
      }
      return newValues;
    });
  }, [touched, validateField, validateOnChange]);

  /**
   * Handle input blur
   */
  const handleBlur = useCallback((e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
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
  const handleSubmit = useCallback((onSubmit: (values: T) => void | Promise<void>) => async (e?: React.FormEvent) => {
    e?.preventDefault();

    const allTouched: Record<string, boolean> = {};
    for (const name of Object.keys(validationSchema)) {
      allTouched[name] = true;
    }
    setTouched(allTouched);

    const isValid = validateAll();
    if (!isValid) return;

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
  const reset = useCallback((newInitialValues?: T) => {
    setValues(newInitialValues || initialValues);
    setErrors({});
    setTouched({});
    setIsSubmitting(false);
  }, [initialValues]);

  /**
   * Check if a field has an error
   */
  const hasError = useCallback((name: string) => {
    return touched[name] && !!errors[name];
  }, [touched, errors]);

  /**
   * Get error message for a field
   */
  const getError = useCallback((name: string) => {
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
