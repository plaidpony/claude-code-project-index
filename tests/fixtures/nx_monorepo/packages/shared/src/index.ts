import { isEmail, isString, isNumber } from 'lodash';

export interface User {
  id: number;
  email: string; 
  name: string;
  age?: number;
}

export function validateUser(userData: any): userData is User {
  if (!userData || typeof userData !== 'object') {
    return false;
  }
  
  const { id, email, name, age } = userData;
  
  if (!isNumber(id) || !isString(email) || !isString(name)) {
    return false;
  }
  
  if (!isEmail(email)) {
    return false;
  }
  
  if (age !== undefined && !isNumber(age)) {
    return false;
  }
  
  return true;
}

export function formatUserName(user: User): string {
  return `${user.name} (${user.email})`;
}

export const API_ENDPOINTS = {
  USERS: '/api/users',
  HEALTH: '/health'
} as const;