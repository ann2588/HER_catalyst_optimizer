function index = getExpIndex(data, targetExp)
    % Function to find the index of a given expXXX in the first column of data
    %
    % Inputs:
    %   data      - Table or cell array where the first column contains experiment names
    %   targetExp - String of the target experiment name (e.g., 'exp770')
    %
    % Output:
    %   index     - The row index of the target experiment in the first column

    % Extract the first column
    expList = data(:, 1);

    % Ensure it's in cell format if using a table
    if istable(data)
        expList = table2cell(expList);
    end

    % Find the index of the target experiment
    index = find(strcmp(expList, targetExp), 1);

    % Check if the experiment was found
    if isempty(index)
        warning('Experiment %s not found.', targetExp);
        index = NaN; % Return NaN if not found
    end
end
