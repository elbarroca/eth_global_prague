export function add0x(data: string): string {
    if (!data || typeof data !== 'string') {
        throw new Error('Invalid data provided to add0x: data must be a non-empty string');
    }
    
    if (data.includes('0x')) {
        return data
    }

    return '0x' + data
}